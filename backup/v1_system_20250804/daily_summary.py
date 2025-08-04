"""
每日新闻汇总模块
基于去同质化处理后的数据生成高质量汇总文档
"""
import pandas as pd
import logging
from typing import List, Dict, Optional
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import os
import json

log = logging.getLogger(__name__)

class DailySummaryGenerator:
    """每日汇总生成器"""
    
    def __init__(self, db_url: str, export_dir: str = "/opt/airflow/exports"):
        """
        初始化汇总生成器
        
        Args:
            db_url: 数据库连接URL
            export_dir: 导出目录
        """
        self.engine = create_engine(db_url)
        self.export_dir = export_dir
        os.makedirs(export_dir, exist_ok=True)
        
    def run(self) -> Dict[str, int]:
        """
        执行汇总任务
        
        Returns:
            Dict[str, int]: 汇总统计信息
        """
        log.info("🚀 开始生成每日新闻汇总...")
        
        # 1. 获取去同质化处理后的数据
        df = self._fetch_deduped_data()
        if df.empty:
            log.warning("没有找到去同质化处理后的数据")
            return {"total_records": 0, "summary_topics": 0}
        
        log.info(f"📊 获取到 {len(df)} 条去同质化记录")
        
        # 2. 按主题分组，选择每个主题的代表性新闻
        summary_data = self._generate_summary_by_topics(df)
        
        # 3. 生成汇总文档
        stats = self._generate_summary_document(summary_data)
        
        log.info(f"✅ 汇总完成: {stats}")
        return stats
    
    def _fetch_deduped_data(self) -> pd.DataFrame:
        """获取去同质化处理后的数据"""
        query = """
            SELECT 
                id, title, body, url, source, published_at,
                topic_id, cluster_size, centroid_sim, score,
                event_id, sentiment
            FROM raw_events
            WHERE published_at >= NOW() - INTERVAL '24 HOURS'
              AND topic_id IS NOT NULL
              AND score IS NOT NULL
            ORDER BY topic_id, score DESC, centroid_sim DESC
        """
        
        try:
            df = pd.read_sql(query, self.engine)
            return df
        except Exception as e:
            log.error(f"获取数据失败: {e}")
            return pd.DataFrame()
    
    def _generate_summary_by_topics(self, df: pd.DataFrame) -> List[Dict]:
        """按主题分组，选择代表性新闻"""
        log.info("🔍 按主题生成汇总...")
        
        summary_data = []
        
        for topic_id in df['topic_id'].unique():
            topic_news = df[df['topic_id'] == topic_id].copy()
            
            # 选择该主题下分数最高的新闻作为代表
            best_news = topic_news.iloc[0]
            
            # 收集该主题下的所有新闻
            all_news = topic_news.head(5).to_dict('records')  # 取前5条
            
            # 计算主题平均情感
            mode_val = topic_news['sentiment'].mode() if 'sentiment' in topic_news.columns else []
            avg_sentiment = mode_val.iloc[0] if hasattr(mode_val, 'iloc') and len(mode_val) > 0 else 'neutral'
            
            
            # 智能截断新闻内容
            content = self._smart_truncate_content(best_news['body'])
            
            summary_data.append({
                'topic_id': topic_id,
                'cluster_size': best_news['cluster_size'],
                'representative_news': {
                    'title': best_news['title'],
                    'content': content,
                    'url': best_news['url'],
                    'source': best_news['source'],
                    'score': best_news['score'],
                    'sentiment': '未知' if best_news.get('sentiment') is None or (isinstance(best_news.get('sentiment'), float) and best_news.get('sentiment') != best_news.get('sentiment')) else best_news.get('sentiment', 'neutral')
                },
                'related_news': all_news,
                'event_id': best_news.get('event_id', ''),
                'avg_score': topic_news['score'].mean(),
                'avg_sentiment': avg_sentiment
            })
        
        # 按平均分数排序
        summary_data.sort(key=lambda x: x['avg_score'], reverse=True)
        
        log.info(f"📈 生成了 {len(summary_data)} 个主题的汇总")
        return summary_data
    
    def _smart_truncate_content(self, content: str, max_length: int = 800) -> str:
        """
        智能截断新闻内容
        
        Args:
            content: 原始内容
            max_length: 最大长度限制
            
        Returns:
            截断后的内容
        """
        if not content:
            return ""
        
        # 如果内容长度在限制内，直接返回
        if len(content) <= max_length:
            return content
        
        # 尝试在句子边界截断
        truncated = content[:max_length]
        
        # 查找最后一个句号、问号或感叹号
        sentence_endings = ['.', '!', '?', '。', '！', '？']
        last_sentence_end = -1
        
        for ending in sentence_endings:
            pos = truncated.rfind(ending)
            if pos > last_sentence_end:
                last_sentence_end = pos
        
        # 如果找到句子边界，在句子边界截断
        if last_sentence_end > max_length * 0.7:  # 确保截断点不要太靠前
            truncated = truncated[:last_sentence_end + 1]
        else:
            # 否则在单词边界截断
            last_space = truncated.rfind(' ')
            if last_space > max_length * 0.8:
                truncated = truncated[:last_space]
        
        return truncated + '...'
    
    def _generate_summary_document(self, summary_data: List[Dict]) -> Dict[str, int]:
        """生成汇总文档"""
        log.info("📝 生成汇总文档...")
        
        today = datetime.now().strftime("%Y%m%d")
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"summary_{today}_{timestamp}.log"
        filepath = os.path.join(self.export_dir, filename)
        
        # 生成汇总内容
        content = self._format_summary_content(summary_data, today)
        
        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 同时生成JSON格式的详细数据
        json_filename = f"summary_{today}_{timestamp}.json"
        json_filepath = os.path.join(self.export_dir, json_filename)
        
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2, default=str)
        
        stats = {
            "total_records": sum(item['cluster_size'] for item in summary_data),
            "summary_topics": len(summary_data),
            "log_file": filename,
            "json_file": json_filename
        }
        
        log.info(f"📄 汇总文档已生成: {filename}")
        return stats
    
    def _format_summary_content(self, summary_data: List[Dict], date: str) -> str:
        """格式化汇总内容"""
        content = f"""# 时政视频账号每日新闻汇总 - {date}

## 概述
- 汇总时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- 主题数量: {len(summary_data)}
- 总新闻数: {sum(item['cluster_size'] for item in summary_data)}

## 热门主题汇总

"""
        
        for i, topic in enumerate(summary_data, 1):
            rep_news = topic['representative_news']
            
            content += f"""### {i}. {rep_news['title']}
- **来源**: {rep_news['source']}
- **主题ID**: {topic['topic_id']}
- **聚类大小**: {topic['cluster_size']} 条相关新闻
- **代表性分数**: {rep_news['score']:.2f}
- **平均分数**: {topic['avg_score']:.2f}
- **情感倾向**: {rep_news['sentiment']}
- **事件ID**: {topic['event_id']}

**代表性新闻摘要**:
{rep_news['content']}

**相关新闻**:
"""
            
            # 添加相关新闻，带URL
            for j, news in enumerate(topic['related_news'][:3], 1):  # 只显示前3条
                url_part = f" - [原文链接]({news['url']})" if news.get('url') else ""
                content += f"{j}. {news['title']} ({news['source']}) - 分数: {news['score']:.2f}{url_part}\n"
            
            content += "\n" + "="*80 + "\n\n"
        
        return content

def run():
    """主入口函数"""
    # 从环境变量获取数据库配置
    db_url = os.getenv('DATABASE_URL', 'postgresql://airflow:airflow@postgres:5432/airflow')
    
    generator = DailySummaryGenerator(db_url)
    return generator.run()

if __name__ == "__main__":
    result = run()
    print(f"汇总完成: {result}") 