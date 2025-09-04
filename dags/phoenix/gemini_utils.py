"""
Gemini 选题卡片生成工具模块

本模块封装了与 Google Vertex AI（Gemini 2.5 Pro 模型）交互的全部核心逻辑，
包含客户端初始化、重试/退避、流式与非流式响应处理、以及从 Phoenix 摘要
JSON 生成结构化 Markdown 选题卡片的高层函数。所有运行参数均优先通过
Airflow Variables 管理，便于在生产环境按需调整；在本地非 Airflow 环境下，
可通过同名环境变量进行覆盖以便调试。

关键变量（Airflow Variables / 环境变量）：
- google_cloud_project：GCP 项目 ID
- google_cloud_location：Vertex 区域（默认 us-central1）
- gemini_model_id：模型 ID（默认 gemini-2.5-pro）
- gemini_system_instruction：系统提示词（指导输出风格/规则）
- gemini_temperature、gemini_top_p：采样参数
- gemini_max_output_tokens：最大输出 token 数
- gemini_streaming_enabled：是否启用流式
- gemini_request_timeout_seconds：单次调用超时时间（秒）
- gemini_max_retries：最大重试次数
- gemini_user_prompt_template：用户提示词模板（支持注入文件名与摘要内容）

返回值约定：除非特别说明，函数失败会抛出异常，成功返回文本字符串或 None。
"""
import os
import os
import logging
import time
import random
from typing import Iterable
import concurrent.futures

# 捕获因在非Airflow环境测试时可能出现的Variable导入失败
try:
    from airflow.models import Variable
except ImportError:
    print("Could not import Airflow Variables. Using dummy values for local testing.")
    class Variable:  # type: ignore
        @staticmethod
        def get(key, default_var=None, deserialize_json=False):
            return os.getenv(key.upper(), default_var)

# 导入Google GenAI新SDK
from google import genai
from google.genai import types
from google.api_core import exceptions as google_exceptions
import httpx
import httpcore
import grpc

# 报警邮件
from phoenix.email_utils import send_alert_email

# 初始化日志
log = logging.getLogger(__name__)

# --- 从Airflow Variables安全地读取配置 ---
# 这种方式允许在本地非Airflow环境中通过环境变量进行测试
PROJECT_ID = Variable.get("google_cloud_project", default_var="your-gcp-project-id")
LOCATION = Variable.get("google_cloud_location", default_var="us-central1")
MODEL_ID = Variable.get("gemini_model_id", default_var="gemini-2.5-pro")
SYSTEM_INSTRUCTION = Variable.get(
    "gemini_system_instruction",
    default_var="你现在是一名时政自媒体的 AI 选题编辑，目标：在给定的新闻 / 推文原始数据里，筛选出最具讨论度的 10 条，输出符合频道标准的选题卡片。"
)
TEMPERATURE = float(Variable.get("gemini_temperature", default_var=0.3))

# 生成调用控制（均可通过 Airflow Variables 覆盖）
REQUEST_TIMEOUT_SECONDS = int(Variable.get("gemini_request_timeout_seconds", default_var=300))
MAX_RETRIES = int(Variable.get("gemini_max_retries", default_var=3))
STREAMING_ENABLED = str(Variable.get("gemini_streaming_enabled", default_var="true")).lower() == "true"
MAX_OUTPUT_TOKENS = int(Variable.get("gemini_max_output_tokens", default_var=8192))
TOP_P = float(Variable.get("gemini_top_p", default_var=0.9))
USER_PROMPT_TEMPLATE = Variable.get(
    "gemini_user_prompt_template",
    default_var="""
所有选题都从文件{source_filename}中选出10个不同话题的选题新闻。新闻内容必须符合频道选题要求，排除常态冲突中包含的事件。按照给定格式输出。从以上文档内选取24小时内发布的符合频道选题标准的新闻。并附上url。同样的事件不要多次出现，尽量多样化。

### 爆点词
“大规模空袭”,“停火破裂”,“泄密录音”,“贪腐证据”,“关键人物遇袭”,“被捕”,“辞职声明”,“弹劾案”,“资金黑洞”

### 常态冲突词
“加沙”,“以色列”,“哈马斯”,“俄乌”,“炮击”,“无人机”,“前线”,“制裁”,“反攻”“中国政府内幕”，“新冠疫苗”，“中国政府”，“中国海军”，“中国武警”，“中国台湾”。

### 说明
- “常态冲突池”仍采用原来的关键词表（加沙、俄乌等）。自然灾害相关如果是常规报道，没有官方相关符合频道要求的，也尽量不选。
- 只要同条推文同时触发「爆点」或「内幕」标记，就视为例外，仍可继续评分。
- 该过滤发生在评分与去重之前，确保纯常态内容完全不会出现在最终 10 条选题里。

### 新闻内容要求
• 时效性：反映24小时内事件，优先突发性或最新动态。
• 高信息密度：整合背景、参与方、进展、数据及影响，结构化且丰富，尽量选择权威媒体。
• 趣味性或影响或反差（任选其一）：
  o 趣味性（吃瓜）：戏剧性细节，激发情感共鸣或讨论。
  o 深远影响（小见大）：从小事件提炼大趋势。
  o 反差：预期与现实差异，制造认知冲击。精准触达中国观众的“痛点”（如技术封锁、外部打压）或“爽点”（如技术突破、外交胜利、对手困境）。包含清晰的国家间、阵营间或文明间的冲突、竞争元素。超越主流报道的独特信息、稀缺数据或深度分析。

### 输出格式（严格遵循，生成恰好10条）
选题1
涉及地区/热点： #地区或#话题 标签若干（例如：#英国 #火灾 #纺织厂）
标题：
副标题：
内容：事件：……；背景：……；看点：……（结构化、信息密度高，必要时注明“以上信息基于媒体报道，尚待进一步核实。”）
时间：YYYY-MM-DD（对应新闻发布时间，需在最近24小时内）
来源：域名 – 完整URL（如：bbc.com – https://www.bbc.com/…）

选题2
涉及地区/热点： …
标题：
副标题：
内容：事件：……；背景：……；看点：……
时间：YYYY-MM-DD
来源：域名 – 完整URL

…（共10条，选题编号依次递增到 选题10）

其他硬性要求：
- 仅从文件 {source_filename} 所包含的文章中选择；
- 同一事件不得重复出现（去重后保留信息量更高的一条）；
- 优先保留触发“爆点词”的新闻；
- 命中“常态冲突词”的新闻需要剔除，除非同时触发“爆点”或“内幕”例外；
- 为每条选题附上来源域名与可点击URL；
- 严格输出10条，不要输出任何额外解释或总结。

以下为该文件的新闻摘要JSON内容：
---
{summary_content}
---
"""
)


def init_genai_client():
    """
    初始化 Google GenAI 客户端。

    说明：
    - 在 Airflow 生产环境中，认证通过容器内挂载的 GCP 服务账号 JSON 自动完成；
      环境变量 `GOOGLE_APPLICATION_CREDENTIALS` 已在 docker-compose 中设置。
    - 在本地调试时，可通过 `gcloud auth application-default login` 或显式设置
      `GOOGLE_APPLICATION_CREDENTIALS` 指向 JSON 文件来完成认证。

    Returns:
        genai.Client: 已就绪的 Gemini 客户端实例。
    """
    log.info(f"Initializing Google GenAI client for project '{PROJECT_ID}' in location '{LOCATION}'...")
    try:
        client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location=LOCATION,
        )
        log.info("Google GenAI client initialized successfully.")
        return client
    except Exception as e:
        log.error(f"Failed to initialize Google GenAI client: {e}")
        raise


def _is_retryable_error(err: Exception) -> bool:
    """判断异常是否可重试。"""
    if isinstance(err, (google_exceptions.ServiceUnavailable, google_exceptions.DeadlineExceeded)):
        return True
    if isinstance(err, grpc.RpcError):
        status = err.code()
        return status in (grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED)
    # 本地客户端侧超时也允许重试
    if isinstance(err, TimeoutError):
        return True
    # httpx/httpcore 断连等瞬时网络错误视为可重试
    if isinstance(err, (httpx.RemoteProtocolError, httpcore.RemoteProtocolError, httpx.ConnectError, httpx.ReadError)):
        return True
    # 空响应也视为可重试（可能是瞬时问题或被流式聚合忽略）
    if isinstance(err, ValueError) and "Empty response text from Gemini" in str(err):
        return True
    # Vertex SDK 某些情况下会在访问 response.text 时抛 ValueError，统一视作可重试
    if isinstance(err, ValueError) and (
        "Cannot get the response text" in str(err)
        or "Cannot get the Candidate text" in str(err)
        or "content has no parts" in str(err)
    ):
        return True
    return False


def _sleep_with_jitter(base_seconds: float) -> None:
    """带抖动的睡眠，减少雪崩效应。"""
    jitter = random.uniform(0, base_seconds * 0.3)
    time.sleep(base_seconds + jitter)


def _accumulate_stream_text(responses: Iterable) -> str:
    """从旧 SDK 流式响应增量累积文本。"""
    parts: list[str] = []
    for chunk in responses:
        try:
            text_piece = getattr(chunk, "text", None)
            if text_piece:
                parts.append(text_piece)
                continue

            # 回退解析 candidates -> content -> parts[].text
            candidates = getattr(chunk, "candidates", None)
            if candidates:
                for cand in candidates:
                    content = getattr(cand, "content", None)
                    if not content:
                        continue
                    content_parts = getattr(content, "parts", None) or []
                    for p in content_parts:
                        p_text = getattr(p, "text", None)
                        if p_text:
                            parts.append(p_text)
        except Exception:
            continue
    return "".join(parts).strip()


def _accumulate_stream_text_genai(responses: Iterable) -> str:
    """从新 SDK 流式响应增量累积文本。"""
    parts: list[str] = []
    for chunk in responses:
        try:
            text_piece = getattr(chunk, "text", None)
            if text_piece:
                parts.append(text_piece)
        except Exception:
            continue
    return "".join(parts).strip()


def _extract_text_from_response(response) -> str:
    """从旧 SDK 非流式响应对象中尽可能抽取文本。"""
    # 避免直接访问触发 SDK 抛错
    try:
        text_value = response.text  # type: ignore[attr-defined]
    except Exception:
        text_value = None
    if text_value:
        try:
            return str(text_value).strip()
        except Exception:
            pass
    # 兼容 candidates -> content -> parts[].text
    try:
        candidates = getattr(response, "candidates", None)
        if candidates:
            parts: list[str] = []
            for cand in candidates:
                content = getattr(cand, "content", None)
                if not content:
                    continue
                content_parts = getattr(content, "parts", None) or []
                for p in content_parts:
                    p_text = getattr(p, "text", None)
                    if p_text:
                        parts.append(p_text)
            if parts:
                return "".join(parts).strip()
    except Exception:
        pass
    return ""


def _extract_text_from_response_genai(response) -> str:
    """从新 SDK 非流式响应对象中抽取文本。"""
    try:
        text_value = getattr(response, "text", None)
        if text_value:
            return str(text_value).strip()
    except Exception:
        pass
    return ""


def _call_generate_with_timeout(
    client,
    model_name: str,
    user_prompt: str,
    generation_config,
    stream: bool,
    timeout_seconds: int,
) -> str:
    """在独立线程中调用 GenAI API，并在超时时抛出 TimeoutError。"""
    def worker() -> str:
        contents = [
            types.Content(
                role="user",
                parts=[types.Part(text=user_prompt)]
            )
        ]
        
        if stream:
            responses = client.models.generate_content_stream(
                model=model_name,
                contents=contents,
                config=generation_config,
            )
            return _accumulate_stream_text_genai(responses)
        else:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=generation_config,
            )
            return _extract_text_from_response_genai(response)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(worker)
        return future.result(timeout=timeout_seconds)


def generate_topic_cards_from_summary(summary_content: str, source_filename: str) -> str:
    """
    将 Phoenix 生成的摘要 JSON 字符串转换为结构化 Markdown 选题卡片。

    Args:
        summary_content (str): Phoenix 摘要文件的 JSON 文本内容。
        source_filename (str): 摘要文件名，仅用于提示词中标注来源。

    Returns:
        str: Gemini 模型生成的 Markdown 报告文本（包含恰好 10 条选题）。
    """
    client = init_genai_client()

    log.info(f"Preparing to call Gemini model '{MODEL_ID}'...")

    # 从 Variable 渲染用户提示模板
    user_prompt = USER_PROMPT_TEMPLATE.format(
        source_filename=source_filename,
        summary_content=summary_content,
    )

    input_size_bytes = len(summary_content.encode("utf-8"))
    
    # 构建新 SDK 的配置
    generation_config = types.GenerateContentConfig(
        temperature=TEMPERATURE,
        top_p=TOP_P,
        max_output_tokens=65535,  # 不限制输出长度
        safety_settings=[
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH",
                threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT",
                threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_CIVIC_INTEGRITY",
                threshold="OFF"
            ),
        ],
        thinking_config=types.ThinkingConfig(
            thinking_budget=-1,  # 不限制思考预算
        ),
        system_instruction=SYSTEM_INSTRUCTION,
        # 禁用自动功能调用 (AFC)
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(
                mode=types.FunctionCallingConfigMode.NONE
            )
        ),
    )

    # 重试（指数退避：1s, 4s, 10s + 抖动）
    backoff_plan = [1, 4, 10]


    for attempt in range(1, MAX_RETRIES + 1):
        # 首次尝试优先使用流式，后续尝试切换为非流式以规避流式偶发空响应
        use_stream = STREAMING_ENABLED and attempt == 1
        log.info(
            f"Sending request to Gemini API (attempt {attempt}/{MAX_RETRIES}) | "
            f"project={PROJECT_ID} location={LOCATION} model={MODEL_ID} "
            f"timeout={REQUEST_TIMEOUT_SECONDS}s streaming={use_stream} "
            f"max_output_tokens={MAX_OUTPUT_TOKENS} input_size_bytes={input_size_bytes}"
        )

        try:
            # 非流式时可设置响应格式（新 SDK 中直接在 config 中指定）
            call_config = generation_config
            if not use_stream:
                # 创建新的配置对象，设置 response_mime_type
                call_config = types.GenerateContentConfig(
                    temperature=generation_config.temperature,
                    top_p=generation_config.top_p,
                    max_output_tokens=generation_config.max_output_tokens,
                    safety_settings=generation_config.safety_settings,
                    thinking_config=generation_config.thinking_config,
                    system_instruction=generation_config.system_instruction,
                    tool_config=generation_config.tool_config,
                    response_mime_type="text/plain",
                )
            
            final_text = _call_generate_with_timeout(
                client=client,
                model_name=MODEL_ID,
                user_prompt=user_prompt,
                generation_config=call_config,
                stream=use_stream,
                timeout_seconds=REQUEST_TIMEOUT_SECONDS,
            )

            if use_stream and not final_text:
                log.warning("Streaming response empty, falling back to non-streaming within the same attempt...")
                fallback_config = types.GenerateContentConfig(
                    temperature=generation_config.temperature,
                    top_p=generation_config.top_p,
                    max_output_tokens=generation_config.max_output_tokens,
                    safety_settings=generation_config.safety_settings,
                    thinking_config=generation_config.thinking_config,
                    system_instruction=generation_config.system_instruction,
                    tool_config=generation_config.tool_config,
                    response_mime_type="text/plain",
                )
                final_text = _call_generate_with_timeout(
                    client=client,
                    model_name=MODEL_ID,
                    user_prompt=user_prompt,
                    generation_config=fallback_config,
                    stream=False,
                    timeout_seconds=REQUEST_TIMEOUT_SECONDS,
                )

            if not final_text:
                raise ValueError("Empty response text from Gemini.")

            log.info("Successfully received response from Gemini API.")
            # 若不完整，按块续写直至 10 条
            try:
                import re
                def _find_last_topic_index(text: str) -> int:
                    nums = [int(n) for n in re.findall(r"选题\s*(\d+)", text)]
                    return max(nums) if nums else 0

                last_idx = _find_last_topic_index(final_text)
                if last_idx < 10:
                    log.info(f"Detected incomplete output (last topic index={last_idx}). Will request continuation in blocks...")
                    next_idx = last_idx + 1
                    while next_idx <= 10:
                        end_idx = min(next_idx + 4, 10)
                        continuation_prompt = f"""
继续输出从“选题{next_idx}”到“选题{end_idx}”的内容，严格延续相同格式：

选题{next_idx}
涉及地区/热点：
标题：
副标题：
内容：事件：……；背景：……；看点：……
时间：YYYY-MM-DD
来源：域名 – 完整URL

…（直到 选题{end_idx}，完成后立即停止，不要多输出）

请仅基于文件 {source_filename} 的同一份摘要继续，不要重复已生成的选题；严格使用中文输出；不要添加任何额外说明或总结。
"""

                        # 针对续写单独做重试
                        for cont_attempt in range(1, MAX_RETRIES + 1):
                            log.info(
                                f"Sending continuation request (topics {next_idx}-{end_idx}) attempt {cont_attempt}/{MAX_RETRIES} | "
                                f"streaming=False"
                            )
                            try:
                                cont_config = types.GenerateContentConfig(
                                    temperature=generation_config.temperature,
                                    top_p=generation_config.top_p,
                                    max_output_tokens=generation_config.max_output_tokens,
                                    safety_settings=generation_config.safety_settings,
                                    thinking_config=generation_config.thinking_config,
                                    system_instruction=generation_config.system_instruction,
                                    tool_config=generation_config.tool_config,
                                    response_mime_type="text/plain",
                                )
                                cont_text = _call_generate_with_timeout(
                                    client=client,
                                    model_name=MODEL_ID,
                                    user_prompt=user_prompt + "\n\n" + continuation_prompt,
                                    generation_config=cont_config,
                                    stream=False,
                                    timeout_seconds=REQUEST_TIMEOUT_SECONDS,
                                )
                                if not cont_text:
                                    raise ValueError("Empty response text from Gemini (continuation).")
                                # 拼接
                                if final_text and not final_text.endswith("\n"):
                                    final_text += "\n"
                                final_text += cont_text.strip() + "\n"
                                break
                            except Exception as ce:
                                cont_retryable = _is_retryable_error(ce)
                                log.error(
                                    f"Continuation failed (topics {next_idx}-{end_idx}) on attempt {cont_attempt}/{MAX_RETRIES}: {ce} | retryable={cont_retryable}"
                                )
                                if cont_attempt >= MAX_RETRIES or not cont_retryable:
                                    raise
                                delay = backoff_plan[min(cont_attempt - 1, len(backoff_plan) - 1)]
                                log.info(f"Retrying continuation after {delay}s + jitter...")
                                _sleep_with_jitter(delay)

                        next_idx = end_idx + 1
            except Exception as cont_e:
                log.error(f"Continuation process failed: {cont_e}")
                raise

            return final_text

        except Exception as e:
            is_retryable = _is_retryable_error(e)
            log.error(
                f"Gemini API call failed on attempt {attempt}/{MAX_RETRIES}: {e} | "
                f"retryable={is_retryable}"
            )

            # 最后一击或不可重试 → 报警并抛出
            if attempt >= MAX_RETRIES or not is_retryable:
                try:
                    body = (
                        f"DAG: gemini_card_generation_dag\n"
                        f"Task: find_and_generate_cards\n"
                        f"Error: {repr(e)}\n\n"
                        f"Context:\n"
                        f"- project: {PROJECT_ID}\n"
                        f"- location: {LOCATION}\n"
                        f"- model_id: {MODEL_ID}\n"
                        f"- streaming_enabled: {STREAMING_ENABLED}\n"
                        f"- timeout_seconds: {REQUEST_TIMEOUT_SECONDS}\n"
                        f"- max_output_tokens: {MAX_OUTPUT_TOKENS}\n"
                        f"- temperature: {TEMPERATURE}\n"
                        f"- top_p: {TOP_P}\n"
                        f"- attempts: {attempt}/{MAX_RETRIES}\n"
                        f"- retryable: {is_retryable}\n"
                        f"- input_size_bytes: {input_size_bytes}\n"
                        f"- source_file: {source_filename}\n"
                    )
                    send_alert_email(
                        subject="[Phoenix][Gemini] 生成失败（503/UNAVAILABLE/超时）",
                        body=body,
                    )
                except Exception:
                    # 报警失败不再中断
                    pass
                raise

            # 计划重试
            delay = backoff_plan[min(attempt - 1, len(backoff_plan) - 1)]
            log.info(f"Retrying Gemini API call after {delay}s + jitter...")
            _sleep_with_jitter(delay)


