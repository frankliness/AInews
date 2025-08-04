"""
摘要处理工具模块 - 统一处理 OpenAI 摘要生成逻辑
"""
import os
import re
import textwrap
import logging
from typing import Tuple, Optional
from datetime import datetime

from openai import OpenAI
from dotenv import load_dotenv

# 环境初始化
load_dotenv(override=True)
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

if not OPENAI_KEY:
    raise RuntimeError("❌ OPENAI_API_KEY 尚未设置！")

client = OpenAI(api_key=OPENAI_KEY)
logger = logging.getLogger(__name__)

# 正则表达式 - 支持匹配 ```cn ...``` 三个反引号 + cn 可能前后有空格 + 换行
CN_BLOCK = re.compile(r"``` *[cC][nN] *\n([\s\S]*?)```")
EN_BLOCK = re.compile(r"``` *[eE][nN] *\n([\s\S]*?)```")

def parse_two_blocks(raw: str) -> Tuple[str, str]:
    """从 raw 文本中提取 ```cn…``` 和 ```en…``` 两段，返回 (中文, 英文)。"""
    cn_m = CN_BLOCK.search(raw)
    en_m = EN_BLOCK.search(raw)
    if not (cn_m and en_m):
        logger.error("未能解析到代码块，原始返回：\n%s", raw)
        raise ValueError("❌ 未找到符合格式的 cn/en 代码块")

    def _clean(txt: str) -> str:
        # 去掉开头可能的注释行 "# 中文段" 或 "#English段"
        txt = re.sub(r"^#.*\n?", "", txt.strip(), flags=re.I)
        return txt.strip()

    return _clean(cn_m.group(1)), _clean(en_m.group(1))

def build_prompt(title: str, body: str) -> str:
    """构建摘要生成提示词"""
    article = f"{title}\n\n{body}"
    return textwrap.dedent(f"""
        你是中文时政媒体策划，请给下面的 Reuters 新闻写「时政视频账号」风格摘要：
        • 输出两段：先中文 ≤110字，再英文 ≤110 words。
        • 结构：①事件→②背景→③看点；不要煽情模板句。
        • 使用 Markdown 代码块：
          ```cn
          #中文段
          ```
          ```en
          #English段
          ```
        ===
        {article}
        ===
    """)

def generate_summary(title: str, body: str, temperature: float = 0.3) -> Tuple[str, str]:
    """生成中英双语摘要"""
    try:
        prompt = build_prompt(title, body)
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        text_out = resp.choices[0].message.content
        cn, en = parse_two_blocks(text_out)
        logger.info("摘要生成成功，长度：cn=%d, en=%d", len(cn), len(en))
        return cn, en
    except Exception as e:
        logger.error("摘要生成失败：%s", e)
        raise 