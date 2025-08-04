"""
通用 EventRegistry v1 封装（免费版本）：
    https://eventregistry.org/documentation
"""
from __future__ import annotations
import os, logging, time, json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .base import ScrapedItem, BaseScraper
from .utils import is_within_24h, log_news_record, check_duplicate_url, simple_sentiment_analysis

log = logging.getLogger(__name__)
_ENDPOINT = "https://eventregistry.org/api/v1/article/getArticles"

def _get_api_key():
    """获取 API key，如果未设置则抛出异常"""
    apikey = os.getenv("EVENTREGISTRY_APIKEY")
    if not apikey:
        raise RuntimeError("缺少环境变量 EVENTREGISTRY_APIKEY")
    return apikey

def _create_session():
    """创建带有重试机制的会话"""
    session = requests.Session()
    
    # 配置重试策略
    retry_strategy = Retry(
        total=3,  # 最多重试3次
        backoff_factor=1,  # 重试间隔：1, 2, 4秒
        status_forcelist=[429, 500, 502, 503, 504],  # 这些状态码会重试
        allowed_methods=["POST", "GET"]  # 允许重试的HTTP方法
    )
    
    # 配置适配器
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

def _event_date_time(article: Dict) -> datetime:
    # EventRegistry 字段 dateTimePub 形如 '2025-07-09T07:16:42Z'
    ts = article.get("dateTimePub") or article.get("dateTime")
    if not ts:
        # 如果没有时间字段，使用当前时间
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)

def _extract_event_info(article: Dict) -> Dict[str, Any]:
    """提取EventRegistry事件信息"""
    # 提取event_id
    event_id = article.get("eventUri") or article.get("eventId")
    
    # 提取embedding（如果存在）
    embedding = None
    if "embedding" in article:
        embedding = json.dumps(article["embedding"])
    
    # 提取事件文章总数
    total_articles_24h = article.get("totalArticleCount", 0)
    
    # 提取源重要性
    source_importance = article.get("sourceImportance", 1)
    
    # 提取权重
    weight = article.get("wgt", 1)
    
    return {
        "event_id": event_id,
        "embedding": embedding,
        "total_articles_24h": total_articles_24h,
        "source_importance": source_importance,
        "weight": weight
    }

def fetch_articles(query: Dict) -> List[Dict]:
    """获取文章列表，带有重试机制"""
    payload = {**query, "apiKey": _get_api_key()}
    
    # 使用更长的超时时间
    timeout = (30, 60)  # (连接超时, 读取超时)
    
    try:
        session = _create_session()
        resp = session.post(_ENDPOINT, json=payload, timeout=timeout)
        resp.raise_for_status()
        results = resp.json().get("articles", {}).get("results", [])
        
        # 检查API返回的数据量，但不强制限制
        requested_count = query.get("count", 50)
        if len(results) > requested_count:
            log.warning(f"API返回 {len(results)} 条数据，超过请求的 {requested_count} 条")
        
        return results
        
    except requests.exceptions.Timeout as e:
        log.error(f"EventRegistry API 请求超时: {e}")
        raise
    except requests.exceptions.ConnectionError as e:
        log.error(f"EventRegistry API 连接错误: {e}")
        raise
    except requests.exceptions.RequestException as e:
        log.error(f"EventRegistry API 请求失败: {e}")
        raise
    except Exception as e:
        log.error(f"EventRegistry API 未知错误: {e}")
        raise

class BaseNewsAPIScraper(BaseScraper):
    """子类只要给出 self.query（keyword / sourceUri / lang…）"""

    query: Dict = {}
    source: str = "newsapi"

    def fetch(self):
        try:
            return fetch_articles(self.query)
        except Exception as e:
            log.error(f"抓取失败 {self.source}: {e}")
            return []  # 返回空列表而不是抛出异常

    def parse(self, raw, db_connection=None):
        collected_at = datetime.now(ZoneInfo("Asia/Shanghai"))
        
        # 统计变量
        total_processed = 0
        sentiment_filtered = 0
        
        for art in raw:
            # 解析发布时间
            published_at = _event_date_time(art)
            
            # 时间过滤：只处理过去24小时内的数据
            if not is_within_24h(published_at):
                log.debug(f"跳过过期数据: {art.get('title', 'Unknown')[:50]}...")
                continue
            
            # 获取基本信息
            title = art.get("title") or ""
            body = art.get("body") or ""
            url = art.get("url")
            sentiment = art.get("sentiment")
            if sentiment is None:
                sentiment = 0.0
            
            # 提取EventRegistry事件信息
            event_info = _extract_event_info(art)
            
            # 如果没有情感分析，进行简单分析
            if sentiment == 0.0:
                sentiment = simple_sentiment_analysis(title + " " + body)
            
            # 统计处理数量
            total_processed += 1
            
            # 情感过滤：只保留情感值大于0.3或小于-0.3的新闻
            if not (sentiment > 0.3 or sentiment < -0.3):
                sentiment_filtered += 1
                log.debug(f"跳过情感值中性的新闻: {art.get('title', 'Unknown')[:50]}... (sentiment: {sentiment:.3f})")
                continue
            
            # 去重检查
            if db_connection and url:
                if check_duplicate_url(url, db_connection):
                    log.debug(f"跳过重复URL: {url}")
                    continue
            
            # 记录到日志文件（不触发汇总）
            try:
                log_news_record(
                    source=self.source,
                    collected_at=collected_at,
                    published_at=published_at,
                    title=title,
                    body=body,
                    url=url,
                    sentiment=sentiment,
                    weight=event_info["weight"],
                    relevance=art.get("relevance", 1.0),
                    event_id=event_info["event_id"],
                    embedding=event_info["embedding"],
                    total_articles_24h=event_info["total_articles_24h"],
                    source_importance=event_info["source_importance"]
                )
            except Exception as e:
                log.error(f"记录日志失败: {e}")
            
            yield ScrapedItem(
                source        = self.source,
                title         = title,
                body          = body,
                published_at  = published_at,
                url           = url,
                likes         = 0,
                retweets      = 0,
                event_id      = event_info["event_id"],
                embedding     = event_info["embedding"],
                total_articles_24h = event_info["total_articles_24h"],
                source_importance = event_info["source_importance"],
                weight        = event_info["weight"],
                sentiment     = sentiment
            )
        
        # 输出情感过滤统计
        if total_processed > 0:
            filtered_ratio = sentiment_filtered / total_processed * 100
            log.info(f"📊 {self.source} 情感过滤统计: 处理 {total_processed} 条，过滤 {sentiment_filtered} 条 (过滤率: {filtered_ratio:.1f}%)")
