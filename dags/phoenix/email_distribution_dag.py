"""
选题简报邮件分发 DAG

职责：
- 根据北京时区当日筛选 `gemini_outputs/` 下的 Markdown 报告；
- 调用 `phoenix.email_utils.send_topic_card_email` 渲染 HTML 正文并以附件形式发送；
- 支持通过 `dag_run.conf` 精确指定或覆盖选择策略。
"""
import logging
import logging
from pathlib import Path
import pendulum
import os

from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator

# 捕获因在非Airflow环境测试时可能出现的Variable导入失败
try:
    from airflow.models import Variable
except ImportError:
    print("Could not import Airflow Variables. Using dummy values for local testing.")
    class Variable:
        @staticmethod
        def get(key, default_var=None, deserialize_json=False):
            return os.getenv(key.upper(), default_var)

# 导入我们在里程碑 2 中创建的工具模块
from phoenix.email_utils import send_topic_card_email

log = logging.getLogger(__name__)

# --- 从 Airflow Variables 安全地读取调度与选择策略 ---
try:
    # 默认在北京时间早上 6:30 运行（DAG 已设置 Asia/Shanghai 时区，因此此处直接使用本地时区的 cron）
    EMAIL_DAG_SCHEDULE = Variable.get("email_dag_schedule", default_var="30 6 * * *")
    EMAIL_SELECTION_STRATEGY = Variable.get("email_report_selection_strategy", default_var="latest_daily_single")
except ImportError:
    EMAIL_DAG_SCHEDULE = "30 6 * * *" # 本地测试回退
    EMAIL_SELECTION_STRATEGY = "latest_daily_single"


def find_and_email_reports(**context):
    """
    这是一个 Airflow Task, 它执行以下操作:
    1. 根据“当前执行时间（ts）”计算北京时间当日，查找当天生成的所有 Markdown 报告文件。
    2. 支持 dag_run.conf 覆盖：report_file（str|list）、use_latest_any_date（bool）、date_override（YYYY-MM-DD）。
    3. 调用邮件工具模块将它们发送出去。
    """
    beijing_tz = pendulum.timezone("Asia/Shanghai")

    # 使用实际执行时间 ts 计算北京时间当日，避免 data_interval_start 导致的跨日偏移
    execution_ts = context["ts"]
    execution_dt = pendulum.parse(execution_ts)
    execution_date_beijing_str = execution_dt.in_timezone(beijing_tz).to_date_string()

    dag_run = context.get("dag_run")
    conf = getattr(dag_run, "conf", None) or {}

    gemini_outputs_dir = Path("/opt/airflow/gemini_outputs")

    # 优先级：
    # 1) conf.report_file: 指定文件（可为字符串或字符串列表；相对路径相对于 gemini_outputs_dir）
    # 2) conf.use_latest_any_date: 选择目录下最新的 *.md 文件
    # 3) conf.date_override: 指定日期（YYYY-MM-DD）来查找当天全部报告
    # 4) 默认：按 execution_date_beijing_str 查找当天全部报告
    report_paths: list[Path] = []

    try:
        # 1) 指定文件
        report_file_param = conf.get("report_file") if isinstance(conf, dict) else None
        if report_file_param:
            if isinstance(report_file_param, str):
                report_file_param = [report_file_param]
            for fp in report_file_param:
                p = Path(fp)
                if not p.is_absolute():
                    p = gemini_outputs_dir / fp
                if not p.exists():
                    raise FileNotFoundError(f"report_file not found: {p}")
                report_paths.append(p)
        else:
            # 2) 全局最新（conf 覆盖）
            use_latest_any_date = bool(conf.get("use_latest_any_date", False)) if isinstance(conf, dict) else False
            if use_latest_any_date:
                all_md = list(gemini_outputs_dir.glob("*.md"))
                if not all_md:
                    raise FileNotFoundError(f"No markdown reports found in '{gemini_outputs_dir}'.")
                latest = max(all_md, key=lambda p: p.stat().st_mtime)
                report_paths = [latest]
            else:
                # 3) 变量控制的选择策略（如果 conf 未覆盖）
                date_str = conf.get("date_override") if isinstance(conf, dict) else None
                if not date_str:
                    date_str = execution_date_beijing_str

                # 根据策略选择：latest_daily_single | latest_any | by_date
                if EMAIL_SELECTION_STRATEGY == "latest_any":
                    all_md = list(gemini_outputs_dir.glob("*.md"))
                    if not all_md:
                        raise FileNotFoundError(f"No markdown reports found in '{gemini_outputs_dir}'.")
                    report_paths = [max(all_md, key=lambda p: p.stat().st_mtime)]
                elif EMAIL_SELECTION_STRATEGY == "by_date":
                    report_paths = sorted(gemini_outputs_dir.glob(f"{date_str}_*.md"), key=lambda p: p.stat().st_mtime)
                    if not report_paths:
                        raise FileNotFoundError(
                            f"No report files found for date '{date_str}' in '{gemini_outputs_dir}'. "
                            "Consider dag_run.conf: {\"use_latest_any_date\": true} or {\"report_file\": \"<filename>\"}."
                        )
                else:
                    # latest_daily_single（默认）：当天范围内筛选 *_daily_briefing.md，取最新一个
                    candidates = list(gemini_outputs_dir.glob(f"{date_str}_*_daily_briefing.md"))
                    if not candidates:
                        # 回退为当天所有 *.md 的最新一个
                        candidates = list(gemini_outputs_dir.glob(f"{date_str}_*.md"))
                    if not candidates:
                        raise FileNotFoundError(
                            f"No markdown reports found for date '{date_str}' in '{gemini_outputs_dir}'. "
                            "Consider dag_run.conf: {\"use_latest_any_date\": true} or set email_report_selection_strategy."
                        )
                    report_paths = [max(candidates, key=lambda p: p.stat().st_mtime)]
    except Exception as e:
        log.error(f"Failed to resolve report files from dag_run.conf: {e}")
        raise

    report_file_paths = [str(p) for p in report_paths]
    log.info(f"DAG triggered. Searching for reports generated on the business date: {execution_date_beijing_str}")
    log.info(f"Found {len(report_file_paths)} reports to email for today: {report_file_paths}")

    # --- 调用核心逻辑 ---
    send_topic_card_email(
        report_files=report_file_paths,
        execution_date_str=execution_date_beijing_str
    )


with DAG(
    dag_id='email_distribution_dag',
    start_date=pendulum.datetime(2025, 1, 1, tz="Asia/Shanghai"),
    schedule_interval=EMAIL_DAG_SCHEDULE,
    catchup=False,
    tags=['phoenix', 'gemini', 'email-distribution'],
    doc_md="""
    ### Email Distribution DAG

    **Owner:** Phoenix Team
    **Schedule:** Daily at 06:30 Beijing Time (22:30 UTC).

    This DAG is the final step in the Gemini post-processing pipeline. It performs the following actions:

    1.  **Finds Reports:** Locates all Markdown report files generated by the `gemini_card_generation_dag` for the current date.
    2.  **Sends Email:** Calls the email utility module to send a single email containing all of today's reports. The report content is rendered as HTML in the email body, and the original Markdown files are included as attachments.
    """
) as dag:
    send_email_task = PythonOperator(
        task_id='find_and_send_email_report',
        python_callable=find_and_email_reports,
    )


