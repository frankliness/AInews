"""
Phoenix V2 新闻抓取客户端
使用 eventregistry 库实现事件优先的数据抓取策略
"""
import logging
from datetime import datetime
from typing import List, Dict, Any
import eventregistry as er

log = logging.getLogger(__name__)

class NewsAPIClient:
    """基于 eventregistry 的新一代新闻API客户端"""
    
    def __init__(self, api_key: str):
        """
        初始化客户端
        
        Args:
            api_key: EventRegistry API密钥
        """
        self.api_key = api_key
        self.event_registry = er.EventRegistry(apiKey=api_key)
        log.info("✅ NewsAPIClient 初始化完成")
    
    def fetch_trending_events_uris(self, category_uris: List[str], date_start: datetime) -> List[str]:
        """
        获取热门事件的URI列表
        
        Args:
            category_uris: 分类URI列表
            date_start: 开始日期
            
        Returns:
            List[str]: 事件URI列表
        """
        try:
            # 创建事件查询
            query = er.QueryEventsIter(
                categoryUri=category_uris,
                dateStart=date_start,
                minArticlesInEvent=5  # 硬编码设置最小文章数
            )
            
            # 执行查询 (测试模式：只获取10个事件)
            events = list(query.execQuery(self.event_registry, maxItems=10))
            
            # 提取事件URI
            event_uris = [event.get("uri") for event in events if event.get("uri")]
            
            log.info(f"📊 获取到 {len(event_uris)} 个热门事件")
            return event_uris
            
        except Exception as e:
            log.error(f"❌ 获取热门事件失败: {e}")
            return []
    
    def fetch_rich_articles_for_event(self, event_uri: str) -> List[Dict[str, Any]]:
        """
        获取事件相关的丰富文章数据
        
        Args:
            event_uri: 事件URI
            
        Returns:
            List[Dict[str, Any]]: 文章详情列表
        """
        try:
            # 创建文章查询
            query = er.QueryEventArticlesIter(eventUri=event_uri)
            
            # 执行查询 (测试模式：每个事件只获取10篇文章)
            articles = list(query.execQuery(self.event_registry, maxItems=10))
            
            # 转换数据格式
            rich_articles = []
            for article in articles:
                # 获取来源信息
                source_info = article.get("source", {})
                source_name = source_info.get("title", "") if source_info else ""
                
                article_data = {
                    "title": article.get("title", ""),
                    "body": article.get("body", ""),
                    "url": article.get("url", ""),
                    "published_at": article.get("dateTimePub"),
                    "sentiment": article.get("sentiment", 0.0),
                    "relevance": article.get("relevance", 1.0),
                    "weight": article.get("wgt", 1.0),
                    "event_uri": event_uri,
                    "source_name": source_name,
                    "source_importance": 1,  # 默认值
                    "concepts": [],  # 暂时为空
                    "total_articles_24h": 0,  # 暂时为0
                    "embedding": None  # 暂时为None
                }
                rich_articles.append(article_data)
            
            log.info(f"📰 事件 {event_uri} 获取到 {len(rich_articles)} 篇文章")
            return rich_articles
            
        except Exception as e:
            log.error(f"❌ 获取事件文章失败 {event_uri}: {e}")
            return [] 