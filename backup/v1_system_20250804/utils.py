"""
抓取工具模块 - 实现时间过滤、去重、日志归档等功能
"""
import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import pytz

# 设置时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')
UTC_TZ = pytz.UTC

def is_within_24h(published_at: datetime) -> bool:
    """
    检查发布时间是否在过去24小时内（北京时间）
    
    Args:
        published_at: 发布时间（UTC）
    
    Returns:
        bool: 是否在过去24小时内
    """
    now_beijing = datetime.now(BEIJING_TZ)
    published_beijing = published_at.astimezone(BEIJING_TZ)
    
    # 计算24小时前的时间
    cutoff_time = now_beijing - timedelta(hours=24)
    
    return published_beijing > cutoff_time

def get_file_date(collected_at: datetime) -> str:
    collected_beijing = collected_at.astimezone(BEIJING_TZ)
    if collected_beijing.hour < 6:
        file_date = collected_beijing.date() - timedelta(days=1)
    else:
        file_date = collected_beijing.date()
    return file_date.strftime("%Y-%m-%d")

def get_log_file_path(source: str, collected_at: datetime) -> Path:
    """
    获取日志文件路径
    
    Args:
        source: 数据源名称
        collected_at: 收集时间
    
    Returns:
        Path: 日志文件路径
    """
    file_date = get_file_date(collected_at)
    
    # 新闻源和twitter都输出到 logs/news/ 目录
    if source in ["reuters", "bbc", "nytimes", "apnews", "bloomberg", "theguardian", 
                  "cnn", "ft", "skynews", "elpais", "scmp", "aljazeera", "theverge", "twitter"]:
        log_dir = Path("logs") / "news" / source
    else:
        log_dir = Path("logs") / source
    
    log_dir.mkdir(parents=True, exist_ok=True)
    
    return log_dir / f"{source}_{file_date}.log"

def log_news_record(
    source: str,
    collected_at: datetime,
    published_at: datetime,
    title: str,
    body: str,
    url: str,
    sentiment: float = 0.0,
    weight: int = 0,
    relevance: float = 1.0,
    **kwargs
):
    """
    记录新闻数据到日志文件（带去重功能）
    
    Args:
        source: 数据源
        collected_at: 收集时间
        published_at: 发布时间
        title: 标题
        body: 正文
        url: 链接
        sentiment: 情感分数
        weight: 权重
        relevance: 相关性
        **kwargs: 其他字段
    """
    log_file = get_log_file_path(source, collected_at)
    
    # 去重检查：如果URL已存在于日志文件中，则跳过
    if url and log_file.exists():
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            log_data = json.loads(line)
                            if log_data.get("url") == url:
                                return  # 已存在，跳过记录
                        except json.JSONDecodeError:
                            continue  # 跳过无效的JSON行
        except Exception as e:
            # 如果读取文件失败，继续记录（避免因文件读取错误而丢失数据）
            pass
    
    log_data = {
        "collected_at": collected_at.isoformat(),
        "published_at": published_at.isoformat(),
        "data_type": "news",
        "title": title,
        "body": body,
        "url": url,
        "sentiment": sentiment,
        "weight": weight,
        "relevance": relevance,
        **kwargs
    }
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_data, ensure_ascii=False) + "\n")

def log_tweet_record(
    source: str,
    collected_at: datetime,
    published_at: datetime,
    username: str,
    text: str,
    retweet_count: int = 0,
    reply_count: int = 0,
    like_count: int = 0,
    quote_count: int = 0,
    impression_count: int = 0,
    rate_limit_event: bool = False,
    remaining_calls: Optional[int] = None,
    user_id: str = "",
    **kwargs
):
    """
    记录推文数据到日志文件（带去重功能）
    禁止写入任何 event_type 字段的日志。
    """
    # 禁止写入任何 event_type 日志
    if "event_type" in kwargs:
        return
    log_file = get_log_file_path(source, collected_at)
    # 去重检查：如果推文内容已存在于日志文件中，则跳过
    if text and log_file.exists():
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            log_data = json.loads(line)
                            if log_data.get("text") == text:
                                return  # 已存在，跳过记录
                        except json.JSONDecodeError:
                            continue  # 跳过无效的JSON行
        except Exception as e:
            pass
    log_data = {
        "collected_at": collected_at.isoformat(),
        "published_at": published_at.isoformat(),
        "username": username,
        "user_id": user_id,
        "text": text,
        "retweet_count": retweet_count,
        "reply_count": reply_count,
        "like_count": like_count,
        "quote_count": quote_count,
        "impression_count": impression_count,
        "rate_limit_event": rate_limit_event,
        **kwargs
    }
    if remaining_calls is not None:
        log_data["remaining_calls"] = remaining_calls
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_data, ensure_ascii=False) + "\n")

def check_duplicate_url(url: str, db_connection) -> bool:
    """
    检查URL是否已存在于数据库中
    
    Args:
        url: 文章URL
        db_connection: 数据库连接
    
    Returns:
        bool: 是否已存在
    """
    with db_connection.cursor() as cur:
        cur.execute("SELECT 1 FROM raw_events WHERE url = %s", (url,))
        return cur.fetchone() is not None

def check_duplicate_tweet_id(tweet_id: str, db_connection) -> bool:
    """
    检查推文ID是否已存在于数据库中
    
    Args:
        tweet_id: 推文ID
        db_connection: 数据库连接
    
    Returns:
        bool: 是否已存在
    """
    with db_connection.cursor() as cur:
        cur.execute("SELECT 1 FROM raw_events WHERE url LIKE %s", (f"%{tweet_id}%",))
        return cur.fetchone() is not None

def simple_sentiment_analysis(text: str) -> float:
    """
    简单情感分析
    
    Args:
        text: 文本内容
    
    Returns:
        float: 情感分数 (-1 到 1)
    """
    try:
        from textblob import TextBlob
        blob = TextBlob(text)
        return blob.sentiment.polarity
    except ImportError:
        # 如果没有 TextBlob，使用简单的关键词分析
        positive_words = ['good', 'great', 'excellent', 'positive', 'success', 'win', 'gain']
        negative_words = ['bad', 'terrible', 'negative', 'loss', 'fail', 'crisis', 'problem']
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count == 0 and negative_count == 0:
            return 0.0
        elif negative_count == 0:
            return 0.5
        elif positive_count == 0:
            return -0.5
        else:
            return (positive_count - negative_count) / (positive_count + negative_count) 

def trigger_log_aggregation(source: str, collected_at: datetime):
    """
    触发日志汇总功能
    
    Args:
        source: 数据源
        collected_at: 收集时间
    """
    try:
        from .log_aggregator import LogAggregator
        import logging
        logger = logging.getLogger(__name__)
        # 获取文件日期
        file_date = get_file_date(collected_at)
        target_date = datetime.strptime(file_date, "%Y-%m-%d").date()
        # 创建汇总器并执行汇总
        aggregator = LogAggregator("logs/news")
        result = aggregator.aggregate_daily_logs(target_date)
        if result:
            logger.info(f"日志汇总完成: {result['log']}")
        else:
            logger.debug(f"未找到 {target_date} 的日志文件进行汇总")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"日志汇总失败: {e}")


def log_news_record_with_aggregation(
    source: str,
    collected_at: datetime,
    published_at: datetime,
    title: str,
    body: str,
    url: str,
    sentiment: float = 0.0,
    weight: int = 0,
    relevance: float = 1.0,
    **kwargs
):
    """
    记录新闻数据到日志文件并触发汇总
    
    Args:
        source: 数据源
        collected_at: 收集时间
        published_at: 发布时间
        title: 标题
        body: 正文
        url: 链接
        sentiment: 情感分数
        weight: 权重
        relevance: 相关性
        **kwargs: 其他字段
    """
    # 记录日志
    log_news_record(
        source=source,
        collected_at=collected_at,
        published_at=published_at,
        title=title,
        body=body,
        url=url,
        sentiment=sentiment,
        weight=weight,
        relevance=relevance,
        **kwargs
    )
    
    # 触发汇总
    trigger_log_aggregation(source, collected_at)


def log_tweet_record_with_aggregation(
    source: str,
    collected_at: datetime,
    published_at: datetime,
    username: str,
    text: str,
    retweet_count: int = 0,
    reply_count: int = 0,
    like_count: int = 0,
    quote_count: int = 0,
    impression_count: int = 0,
    rate_limit_event: bool = False,
    remaining_calls: Optional[int] = None,
    user_id: str = "",
    **kwargs
):
    # 禁止写入任何 event_type 日志
    if "event_type" in kwargs:
        return
    log_tweet_record(
        source=source,
        collected_at=collected_at,
        published_at=published_at,
        username=username,
        text=text,
        retweet_count=retweet_count,
        reply_count=reply_count,
        like_count=like_count,
        quote_count=quote_count,
        impression_count=impression_count,
        rate_limit_event=rate_limit_event,
        remaining_calls=remaining_calls,
        user_id=user_id,
        **kwargs
    )
    trigger_log_aggregation(source, collected_at) 