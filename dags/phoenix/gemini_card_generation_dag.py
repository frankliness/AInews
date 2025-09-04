"""
Gemini 选题卡片生成 DAG

职责：
- 找到与逻辑日期对应的 Phoenix 摘要 JSON 文件；
- 调用 `phoenix.gemini_utils` 生成结构化的 Markdown 选题卡片；
- 将结果保存至容器内 `/opt/airflow/gemini_outputs/` 目录（挂载到项目 `gemini_outputs/`）。
"""
import logging
import logging
from datetime import timedelta
from pathlib import Path
import pendulum  # Airflow 推荐使用 pendulum 处理时间

from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable

# 导入我们在里程碑 2 中创建的工具模块
# Airflow 会自动将 dags/ 目录添加到 PYTHONPATH
from phoenix.gemini_utils import generate_topic_cards_from_summary
from phoenix.email_utils import send_alert_email

log = logging.getLogger(__name__)

# --- 从 Airflow Variables 安全地读取调度配置 ---
try:
    # 默认在北京时间早上 6:00 (即前一天的 UTC 22:00) 运行
    # 注意：本DAG已设置 Asia/Shanghai 时区，因此此处应使用本地时区 06:00 的 cron
    GEMINI_DAG_SCHEDULE = Variable.get("gemini_dag_schedule", default_var="0 6 * * *")
except ImportError:
    GEMINI_DAG_SCHEDULE = "0 6 * * *" # 本地测试回退


def find_and_process_summary(**context):
    """
    这是一个 Airflow Task, 它执行以下操作:
    1. 根据“逻辑日期”找到对应的最新 Phoenix 摘要 JSON 文件。
    2. 调用 Gemini 工具模块处理该文件。
    3. 将结果保存为以北京时间命名的 Markdown 文件。
    """
    # Airflow 的 `ds` 宏代表“逻辑日期”（data stamp），格式为 YYYY-MM-DD。
    # 对于一个在北京时间 8 月 5 日 06:00 运行的 DAG，其处理的是 8 月 4 日的数据，
    # 因此它的 `ds` 就是 '2025-08-04'。
    logical_date_str = context["ds"]
    
    # `ts` 宏是 DAG 运行的 UTC 时间戳
    execution_ts = context["ts"]
    execution_dt = pendulum.parse(execution_ts)

    log.info(f"DAG triggered. Logical date (ds): {logical_date_str}. Execution timestamp (ts): {execution_ts}")

    exports_dir = Path("/opt/airflow/exports")

    # --- 读取 dag_run.conf 以支持手动覆盖 ---
    dag_run = context.get("dag_run")
    conf = getattr(dag_run, "conf", None) or {}
    run_id = getattr(dag_run, "run_id", "")
    is_manual_run = run_id.startswith("manual")

    # --- 读取可配置的文件选择策略 ---
    # 可选值：
    # - by_ds: 仅按 ds（逻辑日期）选择当日最新
    # - latest_any: 忽略日期，选择目录下全局最新
    # - by_ds_then_latest: 优先按 ds，若当日没有则退回全局最新
    selection_strategy_default = Variable.get("gemini_file_selection_strategy", default_var="by_ds_then_latest")
    selection_strategy_manual = Variable.get("gemini_manual_selection_strategy", default_var="latest_any")
    active_strategy = selection_strategy_default
    if is_manual_run and selection_strategy_manual:
        active_strategy = selection_strategy_manual
    log.info(f"File selection strategy: default={selection_strategy_default}, manual={selection_strategy_manual}, active={active_strategy}, is_manual_run={is_manual_run}")

    # 支持以下覆盖策略：
    # 1) conf.summary_file: 指定确切文件名或绝对路径
    # 2) conf.use_latest_any_date: 在整个目录内选择最新的 summary_*.json
    # 3) conf.logical_date_override: 覆盖逻辑日期（YYYY-MM-DD），再按日期范围内选择最新文件
    summary_path = None

    try:
        # 优先精确文件
        summary_file_param = conf.get("summary_file") if isinstance(conf, dict) else None
        if summary_file_param:
            candidate = Path(summary_file_param)
            if not candidate.is_absolute():
                candidate = exports_dir / summary_file_param
            if not candidate.exists():
                raise FileNotFoundError(f"summary_file not found: {candidate}")
            summary_path = candidate
        else:
            # 使用配置或 conf 的策略
            use_latest_any_date = bool(conf.get("use_latest_any_date", False)) if isinstance(conf, dict) else False
            # 可选覆盖逻辑日期
            logical_date_override = conf.get("logical_date_override") if isinstance(conf, dict) else None
            if logical_date_override:
                logical_date_str = logical_date_override

            # conf 优先；否则用 active_strategy
            effective_strategy = "latest_any" if use_latest_any_date else active_strategy

            if effective_strategy == "latest_any":
                all_files = list(exports_dir.glob("summary_*.json"))
                if not all_files:
                    raise FileNotFoundError(f"No summary JSON files found in '{exports_dir}'.")
                summary_path = max(all_files, key=lambda p: p.stat().st_mtime)
            elif effective_strategy == "by_ds_then_latest":
                summary_files_for_date = list(exports_dir.glob(f"summary_{logical_date_str}_*.json"))
                if summary_files_for_date:
                    summary_path = max(summary_files_for_date, key=lambda p: p.stat().st_mtime)
                else:
                    all_files = list(exports_dir.glob("summary_*.json"))
                    if not all_files:
                        raise FileNotFoundError(f"No summary JSON files found in '{exports_dir}'.")
                    summary_path = max(all_files, key=lambda p: p.stat().st_mtime)
            else:  # by_ds
                summary_files_for_date = list(exports_dir.glob(f"summary_{logical_date_str}_*.json"))
                if not summary_files_for_date:
                    raise FileNotFoundError(
                        f"Execution failed: No summary JSON file found for logical date '{logical_date_str}' in '{exports_dir}'. "
                        "Consider providing dag_run.conf: {\"use_latest_any_date\": true} or {\"summary_file\": \"<filename>\"}."
                    )
                summary_path = max(summary_files_for_date, key=lambda p: p.stat().st_mtime)
    except Exception as e:
        log.error(f"Failed to resolve summary file from dag_run.conf: {e}")
        # 失败报警（不拦截异常，让任务失败以便重试）
        try:
            send_alert_email(
                subject="[Phoenix][Gemini] 输入文件解析失败",
                body=(
                    f"DAG: gemini_card_generation_dag\n"
                    f"Task: find_and_generate_cards\n"
                    f"Error: {e}\n"
                    f"Hint: 可在手动触发时传入 conf，例如 {{\"use_latest_any_date\": true}} 或 {{\"summary_file\": \"<filename>\"}}。\n"
                )
            )
        except Exception:
            pass
        raise

    log.info(f"Found latest summary file to process: {summary_path.name}")
    summary_content = summary_path.read_text(encoding="utf-8")

    # --- 调用核心逻辑 ---
    log.info("Calling Gemini utility to generate topic cards...")
    markdown_report = generate_topic_cards_from_summary(summary_content, source_filename=summary_path.name)

    # --- 保存输出 ---
    output_dir = Path("/opt/airflow/gemini_outputs")
    output_dir.mkdir(parents=True, exist_ok=True) # 确保目录存在
    
    # 使用北京时间来命名输出文件，确保符合业务需求
    beijing_tz = pendulum.timezone("Asia/Shanghai")
    beijing_now = execution_dt.in_timezone(beijing_tz)
    output_filename = beijing_now.strftime("%Y-%m-%d_%H-%M-%S_daily_briefing.md")
    
    output_path = output_dir / output_filename
    
    output_path.write_text(markdown_report, encoding="utf-8")
    log.info(f"✅ Successfully saved Gemini report to: {output_path}")

    # (可选) 通过 XCom 将文件路径传递给未来的下游任务
    context['ti'].xcom_push(key='gemini_report_path', value=str(output_path))


with DAG(
    dag_id='gemini_card_generation_dag',
    start_date=pendulum.datetime(2025, 1, 1, tz="Asia/Shanghai"),
    schedule_interval=GEMINI_DAG_SCHEDULE,
    catchup=False,
    tags=['phoenix', 'gemini', 'report-generation'],
    doc_md="""
    ### Gemini Topic Card Generation DAG

    **Owner:** Phoenix Team
    **Schedule:** Daily at 06:00 Beijing Time (22:00 UTC).

    This DAG is the first step in the Gemini post-processing pipeline. It performs the following actions:

    1.  **Finds Input:** Locates the latest JSON summary file generated by `summary_generation_dag` for the corresponding logical date.
    2.  **Calls AI:** Invokes the Gemini 2.5 Pro model via a utility module to transform the news summaries into structured topic cards.
    3.  **Saves Output:** Saves the generated report as a Markdown file in the `/gemini_outputs/` directory, named with the Beijing time of execution.
    """
) as dag:
    generate_cards_task = PythonOperator(
        task_id='find_and_generate_cards',
        python_callable=find_and_process_summary,
        # DAG 层面兜底重试与超时
        retries=3,
        retry_exponential_backoff=True,
        retry_delay=pendulum.duration(minutes=2),
        max_retry_delay=pendulum.duration(minutes=10),
        execution_timeout=timedelta(minutes=30),
    )


