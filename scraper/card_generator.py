"""
每日选题卡片生成器
从全量新闻和推文记录中挑选最具价值的15条内容
"""
import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from zoneinfo import ZoneInfo

import psycopg2
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

class DailyCardGenerator:
    """每日选题卡片生成器"""
    
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.batch_tokens = int(os.getenv("GPT_BATCH_TOKENS", "3000"))
        self.max_retries = int(os.getenv("GPT_RETRY_MAX", "3"))
        
        if not self.openai_api_key:
            raise RuntimeError("缺少 OPENAI_API_KEY 环境变量")
        
        # 配置OpenAI客户端
        self.client = OpenAI(api_key=self.openai_api_key)
    
    def read_summary_data(self, date_str: str) -> List[Dict]:
        """读取指定日期的汇总数据"""
        summary_file = Path(f"logs/news/summary/summary_{date_str}.json")
        
        if not summary_file.exists():
            log.warning(f"汇总文件不存在: {summary_file}")
            return []
        
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 提取所有记录
            all_records = []
            for source, source_data in data.get("sources", {}).items():
                for log_entry in source_data.get("logs", []):
                    try:
                        # 处理多行JSON字符串的情况
                        if '\n' in log_entry:
                            # 按换行符分割，每个部分尝试解析为JSON
                            json_parts = log_entry.strip().split('\n')
                            for part in json_parts:
                                if part.strip():
                                    try:
                                        record = json.loads(part.strip())
                                        # 添加来源信息
                                        record["source_name"] = source
                                        all_records.append(record)
                                    except json.JSONDecodeError:
                                        # 跳过无法解析的部分
                                        continue
                        else:
                            # 单行JSON字符串
                            record = json.loads(log_entry)
                            # 添加来源信息
                            record["source_name"] = source
                            all_records.append(record)
                    except json.JSONDecodeError:
                        continue
            
            log.info(f"读取到 {len(all_records)} 条记录")
            return all_records
            
        except Exception as e:
            log.error(f"读取汇总文件失败: {e}")
            return []
    
    def estimate_tokens(self, text: str) -> int:
        """估算文本的token数量（粗略估算）"""
        # 简单估算：1个token约等于4个字符
        return len(text) // 4
    
    def split_large_data(self, records: List[Dict]) -> List[List[Dict]]:
        """将大数据分批，避免token超限"""
        if not records:
            return []
        
        # 将记录转换为JSON字符串
        data_json = json.dumps(records, ensure_ascii=False)
        total_tokens = self.estimate_tokens(data_json)
        
        if total_tokens <= self.batch_tokens:
            return [records]
        
        # 需要分批
        num_batches = (total_tokens // self.batch_tokens) + 1
        batch_size = len(records) // num_batches + 1
        
        batches = []
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            batches.append(batch)
        
        log.info(f"数据过大，分为 {len(batches)} 批处理")
        return batches
    
    def preprocess_records(self, records: List[Dict]) -> List[Dict]:
        """预处理记录，提取关键信息并简化格式"""
        processed_records = []
        
        for record in records:
            processed_record = {}
            
            # 提取标题
            if 'title' in record:
                processed_record['title'] = record['title']
            elif 'text' in record:
                # 对于推文，使用前100字符作为标题
                text = record['text']
                processed_record['title'] = text[:100] + ('...' if len(text) > 100 else '')
            
            # 提取内容
            if 'body' in record:
                processed_record['content'] = record['body']
            elif 'text' in record:
                processed_record['content'] = record['text']
            elif 'description' in record:
                processed_record['content'] = record['description']
            
            # 提取URL
            if 'url' in record:
                processed_record['url'] = record['url']
            
            # 提取时间
            if 'published_at' in record:
                processed_record['date'] = record['published_at'][:10]  # 只取日期部分
            
            # 提取来源
            if 'source' in record:
                processed_record['source'] = record['source']
            elif 'source_name' in record:
                processed_record['source'] = record['source_name']
            
            # 只保留有标题和内容的记录
            if processed_record.get('title') and processed_record.get('content'):
                processed_records.append(processed_record)
        
        return processed_records
    
    def build_prompt(self, records: List[Dict], batch_info: Optional[str] = None) -> str:
        """构建GPT提示词"""
        # 转换为更简洁的格式
        simplified_records = []
        for record in records:
            simplified_record = {
                "title": record.get("title", ""),
                "content": record.get("content", "")[:300],  # 限制内容长度
                "source": record.get("source", ""),
                "date": record.get("date", ""),
                "url": record.get("url", "")
            }
            simplified_records.append(simplified_record)
        
        records_json = json.dumps(simplified_records, ensure_ascii=False, indent=2)
        
        prompt = f"""───────────────────────────────────  SYSTEM  ───────────────────────────────────
你是一名中文时政自媒体策划：  
- 聚焦全球重大政治、经济、军事、科技、文化热点  
- 强调中国视角，信息密度高，拒绝空洞煽情  

【卡片模板】  
{{
  "hashtags": ["#标签1", "#标签2"],      # 2–5 个中文标签，全带 #
  "title": "≤8字主标题",                 # 不得超 8 个汉字
  "subtitle": "≤12字副标题",             # 不得超 12 个汉字
  "summary": "…三段：事件→背景→看点…",  # ≤200 字，段落用空行分隔
  "date": "YYYY-MM-DD",                  # 事件报道日（北京时间）
  "source": "媒体名称 – URL"              # 媒体名与原文链接
}}

【硬性要求】  
1. **仅输出 JSON 数组，恰好 15 条卡片**，按重要度降序。  
2. 所有字段不得缺失或增删；不得输出任何多余文字。  
3. 标签、标题、副标题、摘要均为简体中文；URL 原样保留。  
4. 如同一事件有多条记录，只选信息最完整的一条。  
5. **必须严格按照JSON格式输出，不要添加任何说明文字。**

【内容质量标准】  
- **深度**：话题需具备权威性与复杂性，适合深度分析而非浅层快讯。  
- **来源优先级**：优先选择权威媒体、知名专家或官方机构；如条件允许，优先采用**英文信息源**。  
- **讨论性**：涉及多方利益、历史脉络或未来影响，能激发深入讨论。  

【新闻内容要求】  
- **时效性**：仅考虑过去 24 小时内的事件，突发或最新动态优先。  
- **高信息密度**：摘要需整合背景、参与方、进展、数据与影响，结构化且丰富。  
- **趣味性 / 影响 / 反差**（三选一，至少满足其一）：  
  - *趣味性（吃瓜）*：包含戏剧性细节，激发情感共鸣或讨论；  
  - *深远影响（小见大）*：由小事件透视大趋势，揭示长期影响；  
  - *反差*：呈现预期与现实差异，制造认知冲击。  
───────────────────────────────────────────────────────────────────────────────
───────────────────────────────────  USER  ────────────────────────────────────
以下是 {datetime.now(ZoneInfo("Asia/Shanghai")).strftime('%Y-%m-%d')} 的精选新闻记录（共 {len(records)} 条）。  
{batch_info or ""}
请从全部记录中挑选最具价值、符合以上标准的 15 条，并按卡片模板输出 JSON 数组。  
**重要：只返回JSON数组，不要任何其他文字！**

数据记录：
{records_json}"""
        
        return prompt
    
    def call_gpt(self, prompt: str, retry_count: int = 0) -> Optional[List[Dict]]:
        """调用GPT API"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "你是一名中文时政自媒体策划，聚焦全球重大政治、经济、军事、科技、文化热点，强调中国视角，信息密度高，拒绝空洞煽情。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            content = response.choices[0].message.content.strip()
            
            # 添加调试日志
            log.info(f"GPT返回内容长度: {len(content)} 字符")
            log.info(f"GPT返回内容前200字符: {content[:200]}")
            
            # 尝试解析JSON
            try:
                # 清理内容，移除可能的markdown格式
                cleaned_content = content.strip()
                
                # 提取JSON部分
                if cleaned_content.startswith('[') and cleaned_content.endswith(']'):
                    cards = json.loads(cleaned_content)
                else:
                    # 尝试找到JSON数组
                    start = cleaned_content.find('[')
                    end = cleaned_content.rfind(']') + 1
                    if start != -1 and end != 0 and start < end:
                        json_part = cleaned_content[start:end]
                        cards = json.loads(json_part)
                    else:
                        # 尝试查找JSON数组的其他模式
                        import re
                        json_pattern = r'\[.*?\]'
                        matches = re.findall(json_pattern, cleaned_content, re.DOTALL)
                        if matches:
                            # 使用最长的匹配
                            longest_match = max(matches, key=len)
                            cards = json.loads(longest_match)
                        else:
                            raise ValueError("未找到有效的JSON数组")
                
                # 验证卡片格式
                if self.validate_cards(cards):
                    return cards
                else:
                    raise ValueError("卡片格式验证失败")
                    
            except json.JSONDecodeError as e:
                log.error(f"JSON解析失败: {e}")
                log.error(f"GPT返回内容: {content}")
                raise
                
        except Exception as e:
            log.error(f"GPT调用失败 (重试 {retry_count + 1}/{self.max_retries}): {e}")
            
            if retry_count < self.max_retries - 1:
                return self.call_gpt(prompt, retry_count + 1)
            else:
                log.error("GPT调用最终失败")
                return None
    
    def validate_cards(self, cards: List[Dict]) -> bool:
        """验证卡片格式"""
        if not isinstance(cards, list):
            return False
        
        for card in cards:
            if not isinstance(card, dict):
                return False
            
            # 检查必需字段
            required_fields = ["hashtags", "title", "subtitle", "summary", "date", "source"]
            for field in required_fields:
                if field not in card:
                    log.error(f"缺少必需字段: {field}")
                    return False
            
            # 检查字段长度
            if len(card["title"]) > 8:
                log.error(f"标题过长: {card['title']}")
                return False
            
            if len(card["subtitle"]) > 12:
                log.error(f"副标题过长: {card['subtitle']}")
                return False
            
            if len(card["summary"]) > 200:
                log.error(f"摘要过长: {len(card['summary'])} 字符")
                return False
            
            # 检查标签格式
            if not isinstance(card["hashtags"], list) or len(card["hashtags"]) < 2 or len(card["hashtags"]) > 5:
                log.error(f"标签格式错误: {card['hashtags']}")
                return False
            
            # 检查标签是否带#号
            for tag in card["hashtags"]:
                if not tag.startswith("#"):
                    log.error(f"标签必须以#开头: {tag}")
                    return False
        
        return True
    
    def generate_cards(self, date_str: str, strategy: str = "auto") -> List[Dict]:
        """生成每日卡片
        
        Args:
            date_str: 日期字符串
            strategy: 生成策略 ("auto", "simple", "two_stage", "smart")
        """
        # 读取数据
        records = self.read_summary_data(date_str)
        if not records:
            log.warning("没有数据可处理")
            return []
        
        # 自动策略选择
        if strategy == "auto":
            strategy = self.auto_select_strategy(records)
        
        log.info(f"使用 {strategy} 策略生成卡片，原始数据 {len(records)} 条")
        
        if strategy == "two_stage":
            # 两阶段策略：全局筛选 + 精确生成
            return self.two_stage_generation(records)
        elif strategy == "smart":
            # 智能分批策略：按主题分组处理
            return self.smart_batch_generation(records)
        else:
            # 简单分批策略（原策略）
            processed_records = self.preprocess_records(records)
            batches = self.split_large_data(processed_records)
            
            if len(batches) == 1:
                prompt = self.build_prompt(processed_records)
                return self.call_gpt(prompt) or []
            else:
                all_cards = []
                for i, batch in enumerate(batches, 1):
                    batch_info = f"这是批 {i} / 共 {len(batches)} 批，请暂存，待批 {len(batches)} 后统一输出 15 条结果。"
                    prompt = self.build_prompt(batch, batch_info)
                    cards = self.call_gpt(prompt)
                    if cards:
                        all_cards.extend(cards)
                
                if len(all_cards) > 15:
                    final_prompt = f"""───────────────────────────────────  SYSTEM  ───────────────────────────────────
你是一名中文时政自媒体策划：  
- 聚焦全球重大政治、经济、军事、科技、文化热点  
- 强调中国视角，信息密度高，拒绝空洞煽情  

【硬性要求】  
1. **仅输出 JSON 数组，恰好 15 条卡片**，按重要度降序。  
2. 所有字段不得缺失或增删；不得输出任何多余文字。  
3. 标签、标题、副标题、摘要均为简体中文；URL 原样保留。  

───────────────────────────────────  USER  ────────────────────────────────────
从以下 {len(all_cards)} 条候选卡片中挑选最具价值、符合标准的 15 条，并按卡片模板输出 JSON 数组：

{json.dumps(all_cards, ensure_ascii=False, indent=2)}

───────────────────────────────────────────────────────────────────────────────"""
                    
                    return self.call_gpt(final_prompt) or []
                else:
                    return all_cards
    
    def two_stage_generation(self, records: List[Dict]) -> List[Dict]:
        """两阶段生成：全局筛选 + 精确生成"""
        if not records:
            return []
        
        # 第一阶段：全局筛选，选出候选内容
        stage1_prompt = self.build_stage1_prompt(records)
        candidates = self.call_gpt(stage1_prompt)
        
        if not candidates:
            return []
        
        # 第二阶段：从候选内容中精确生成15条卡片
        stage2_prompt = self.build_stage2_prompt(candidates)
        final_cards = self.call_gpt(stage2_prompt)
        
        return final_cards or []
    
    def build_stage1_prompt(self, records: List[Dict]) -> str:
        """构建第一阶段提示词：全局筛选"""
        processed_records = self.preprocess_records(records)
        
        # 限制数据量，但保持全局视野
        if len(processed_records) > 100:
            # 按时间排序，取最新的100条
            processed_records = sorted(processed_records, 
                                    key=lambda x: x.get('date', ''), 
                                    reverse=True)[:100]
        
        records_json = json.dumps(processed_records, ensure_ascii=False, indent=2)
        
        return f"""你是一名新闻编辑，需要从大量新闻中筛选出最具价值的候选内容。

【任务要求】
1. 从以下{len(processed_records)}条新闻中，选出30-50条最具价值的候选内容
2. 重点关注：重大事件、突发新闻、深度分析、独家报道
3. 避免重复：同一事件只选信息最完整的一条
4. 多样性：涵盖政治、经济、科技、文化等不同领域

【输出格式】
返回JSON数组，每个元素包含：
{{
  "title": "新闻标题",
  "content": "新闻内容摘要（100字内）",
  "importance": "high/medium/low",
  "category": "政治/经济/科技/文化/其他",
  "source": "来源",
  "url": "链接"
}}

【数据】
{records_json}"""
    
    def build_stage2_prompt(self, candidates: List[Dict]) -> str:
        """构建第二阶段提示词：精确生成卡片"""
        candidates_json = json.dumps(candidates, ensure_ascii=False, indent=2)
        
        return f"""你是一名中文时政自媒体策划，需要从候选内容中生成15条精选卡片。

【卡片模板】
{{
  "hashtags": ["#标签1", "#标签2"],
  "title": "≤8字主标题",
  "subtitle": "≤12字副标题", 
  "summary": "≤200字摘要，三段：事件→背景→看点",
  "date": "YYYY-MM-DD",
  "source": "媒体名称 – URL"
}}

【候选内容】
{candidates_json}

【要求】
1. 从候选内容中精选15条，按重要性排序
2. 确保内容多样性，避免重复
3. 严格按照模板格式输出JSON数组
4. 只输出JSON，不要其他文字"""
    
    def save_to_database(self, cards: List[Dict], date_str: str) -> int:
        """保存卡片到数据库"""
        if not self.db_url:
            log.warning("未配置数据库连接，跳过数据库保存")
            return 0
        
        try:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    # 创建表（如果不存在）
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS daily_cards (
                            id BIGSERIAL PRIMARY KEY,
                            card_date DATE NOT NULL,
                            hashtags TEXT[] NOT NULL,
                            title VARCHAR(50) NOT NULL,
                            subtitle VARCHAR(100) NOT NULL,
                            summary TEXT NOT NULL,
                            date VARCHAR(20) NOT NULL,
                            source TEXT NOT NULL,
                            created_at TIMESTAMPTZ DEFAULT now()
                        )
                    """)
                    
                    # 删除当天的旧数据
                    cur.execute("DELETE FROM daily_cards WHERE card_date = %s", (date_str,))
                    
                    # 插入新数据
                    saved_count = 0
                    for card in cards:
                        cur.execute("""
                            INSERT INTO daily_cards 
                            (card_date, hashtags, title, subtitle, summary, date, source)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (
                            date_str,
                            card["hashtags"],
                            card["title"],
                            card["subtitle"],
                            card["summary"],
                            card["date"],
                            card["source"]
                        ))
                        saved_count += 1
                    
                    conn.commit()
                    log.info(f"保存 {saved_count} 条卡片到数据库")
                    return saved_count
                    
        except Exception as e:
            log.error(f"保存到数据库失败: {e}")
            return 0
    
    def generate_markdown(self, cards: List[Dict], date_str: str) -> str:
        """生成Markdown文件"""
        if not cards:
            return ""
        
        # 确保导出目录存在
        export_dir = Path("exports")
        export_dir.mkdir(exist_ok=True)
        
        md_file = export_dir / f"cards_{date_str}.md"
        
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(f"# {date_str} 时政视频账号·每日选题卡片（共 {len(cards)} 条）\n\n")
            
            for i, card in enumerate(cards, 1):
                # 格式化标签（标签已经带#号）
                hashtags = " ".join(card["hashtags"])
                
                f.write(f"## {i}. {card['title']} — {card['subtitle']}\n")
                f.write(f"- **标签**：{hashtags}\n")
                f.write(f"- **来源**：{card['source']}\n")
                f.write(f"- **摘要**\n")
                f.write(f"  > {card['summary']}\n")
                f.write("\n---\n\n")
        
        log.info(f"生成Markdown文件: {md_file}")
        return str(md_file) 

    def smart_batch_generation(self, records: List[Dict]) -> List[Dict]:
        """智能分批生成：按主题分组，保持全局视野"""
        if not records:
            return []
        
        processed_records = self.preprocess_records(records)
        
        # 按主题分组
        topic_groups = self.group_by_topic(processed_records)
        
        all_candidates = []
        
        # 对每个主题组进行筛选
        for topic, group_records in topic_groups.items():
            if len(group_records) <= 20:
                # 小批次直接处理
                candidates = self.process_topic_group(group_records, topic)
                all_candidates.extend(candidates)
            else:
                # 大批次需要进一步分批
                sub_batches = self.split_large_data(group_records)
                for batch in sub_batches:
                    candidates = self.process_topic_group(batch, topic)
                    all_candidates.extend(candidates)
        
        # 最终从所有候选内容中精选15条
        final_prompt = self.build_final_selection_prompt(all_candidates)
        final_cards = self.call_gpt(final_prompt)
        
        return final_cards or []
    
    def group_by_topic(self, records: List[Dict]) -> Dict[str, List[Dict]]:
        """按主题分组"""
        # 简单的关键词分组
        topic_keywords = {
            "政治": ["政府", "选举", "政策", "领导人", "国会", "议会", "总统", "总理"],
            "经济": ["股市", "经济", "GDP", "通胀", "利率", "贸易", "投资", "金融"],
            "科技": ["AI", "人工智能", "科技", "创新", "技术", "互联网", "数字"],
            "军事": ["军队", "武器", "战争", "军事", "国防", "安全"],
            "文化": ["文化", "艺术", "教育", "体育", "娱乐", "电影", "音乐"],
            "其他": []
        }
        
        groups = {topic: [] for topic in topic_keywords.keys()}
        
        for record in records:
            title = record.get('title', '').lower()
            content = record.get('content', '').lower()
            text = title + ' ' + content
            
            assigned = False
            for topic, keywords in topic_keywords.items():
                if topic != "其他" and any(keyword in text for keyword in keywords):
                    groups[topic].append(record)
                    assigned = True
                    break
            
            if not assigned:
                groups["其他"].append(record)
        
        # 移除空组
        return {topic: records for topic, records in groups.items() if records}
    
    def process_topic_group(self, records: List[Dict], topic: str) -> List[Dict]:
        """处理单个主题组"""
        if not records:
            return []
        
        prompt = f"""从以下{topic}相关新闻中，选出5-10条最具价值的候选内容：

【要求】
1. 重点关注重大事件、突发新闻、深度分析
2. 避免重复内容
3. 按重要性排序

【输出格式】
返回JSON数组，每个元素包含：
{{
  "title": "新闻标题",
  "content": "内容摘要（50字内）",
  "importance": "high/medium/low",
  "source": "来源",
  "url": "链接"
}}

【数据】
{json.dumps(records, ensure_ascii=False, indent=2)}"""
        
        candidates = self.call_gpt(prompt)
        return candidates or []
    
    def build_final_selection_prompt(self, candidates: List[Dict]) -> str:
        """构建最终精选提示词"""
        candidates_json = json.dumps(candidates, ensure_ascii=False, indent=2)
        
        return f"""从以下候选内容中，精选出15条最具价值的新闻卡片：

【卡片模板】
{{
  "hashtags": ["#标签1", "#标签2"],
  "title": "≤8字主标题",
  "subtitle": "≤12字副标题",
  "summary": "≤200字摘要，三段：事件→背景→看点",
  "date": "YYYY-MM-DD", 
  "source": "媒体名称 – URL"
}}

【候选内容】
{candidates_json}

【要求】
1. 确保内容多样性，涵盖不同主题
2. 按重要性排序
3. 避免重复事件
4. 严格按照模板格式输出JSON数组""" 

    def auto_select_strategy(self, records: List[Dict]) -> str:
        """自动选择最佳策略
        
        根据数据量、数据特征自动选择最适合的策略
        """
        if not records:
            return "simple"
        
        # 数据预处理
        processed_records = self.preprocess_records(records)
        
        # 计算数据特征
        data_size = len(processed_records)
        data_complexity = self.calculate_data_complexity(processed_records)
        topic_diversity = self.calculate_topic_diversity(processed_records)
        
        print(f"数据特征分析:")
        print(f"- 数据量: {data_size} 条")
        print(f"- 复杂度: {data_complexity:.2f}")
        print(f"- 主题多样性: {topic_diversity:.2f}")
        
        # 策略选择逻辑
        if data_size >= 100:
            # 大数据量，优先考虑质量
            if data_complexity > 0.7:
                strategy = "two_stage"  # 高复杂度用两阶段
                reason = "大数据量+高复杂度，需要全局视野"
            else:
                strategy = "smart"  # 中等复杂度用智能分批
                reason = "大数据量+中等复杂度，智能分批平衡效率"
        elif data_size >= 50:
            # 中等数据量
            if topic_diversity > 0.6:
                strategy = "smart"  # 高多样性用智能分批
                reason = "中等数据量+高多样性，智能分批保持多样性"
            else:
                strategy = "two_stage"  # 低多样性用两阶段
                reason = "中等数据量+低多样性，两阶段提高质量"
        else:
            # 小数据量
            strategy = "simple"  # 小数据量用简单分批
            reason = "小数据量，简单分批效率最高"
        
        print(f"推荐策略: {strategy}")
        print(f"选择理由: {reason}")
        
        return strategy
    
    def calculate_data_complexity(self, records: List[Dict]) -> float:
        """计算数据复杂度"""
        if not records:
            return 0.0
        
        # 计算平均内容长度
        total_length = sum(len(str(record.get('content', ''))) for record in records)
        avg_length = total_length / len(records)
        
        # 计算字段完整性
        complete_fields = 0
        total_fields = len(records) * 5  # 假设5个主要字段
        
        for record in records:
            if record.get('title'): complete_fields += 1
            if record.get('content'): complete_fields += 1
            if record.get('url'): complete_fields += 1
            if record.get('date'): complete_fields += 1
            if record.get('source'): complete_fields += 1
        
        field_completeness = complete_fields / total_fields
        
        # 复杂度 = 平均长度权重 + 字段完整性权重
        complexity = (avg_length / 1000) * 0.6 + field_completeness * 0.4
        return min(complexity, 1.0)
    
    def calculate_topic_diversity(self, records: List[Dict]) -> float:
        """计算主题多样性"""
        if not records:
            return 0.0
        
        # 按主题分组
        topic_groups = self.group_by_topic(records)
        
        # 计算主题分布
        total_records = len(records)
        topic_distribution = []
        
        for topic, group_records in topic_groups.items():
            if topic != "其他":  # 排除"其他"类别
                topic_distribution.append(len(group_records) / total_records)
        
        if not topic_distribution:
            return 0.0
        
        # 计算多样性（使用标准差，值越大越多样）
        import statistics
        diversity = statistics.stdev(topic_distribution) if len(topic_distribution) > 1 else 0.0
        
        # 归一化到0-1范围
        normalized_diversity = min(diversity * 5, 1.0)  # 乘以5是为了放大差异
        
        return normalized_diversity 