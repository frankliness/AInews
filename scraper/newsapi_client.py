# 文件路径: scraper/newsapi_client.py (最终版)

import logging
from datetime import datetime, timedelta
from eventregistry import (
    EventRegistry,
    QueryEventsIter,
    QueryEvent,
    RequestEventArticles,
    ReturnInfo,
    ArticleInfoFlags,
    EventInfoFlags,
    RequestEventsInfo,
    QueryItems
)

log = logging.getLogger(__name__)

class NewsApiClient:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key cannot be empty.")
        self.er = EventRegistry(apiKey=api_key, allowUseOfArchive=False)
        self.source_uri_cache = {}
        log.info("NewsApiClient initialized successfully.")

    def get_source_uri(self, source_name: str):
        if source_name in self.source_uri_cache:
            return self.source_uri_cache[source_name]
        try:
            uri = self.er.getSourceUri(source_name)
            if uri:
                self.source_uri_cache[source_name] = uri
                log.info(f"Translated source '{source_name}' to URI '{uri}'.")
            else:
                log.warning(f"Could not find URI for source '{source_name}'.")
            return uri
        except Exception as e:
            log.error(f"Error fetching URI for source '{source_name}': {e}")
            return None

    def get_uris_for_sources(self, source_names: list):
        return [uri for name in source_names if (uri := self.get_source_uri(name)) is not None]

    def fetch_trending_events(self, source_names: list, max_events: int, use_whitelist: bool = True):
        """获取热门事件，并根据开关决定是否启用信源白名单过滤。"""
        log.info(f"Fetching up to {max_events} trending events...")

        # 【核心修复】: 将所有参数“平铺”开来，作为独立的关键字参数传递
        # 我们不再使用 requestedResult 参数
        # 【核心修复】: 构造一个完全符合SDK三层嵌套结构的"参数套娃"
        # 第一层：创建唯一有效的"主订单" -> RequestEventsInfo
        requested_result = RequestEventsInfo(
            # 第二层：在"主订单"中，填入我们的"备注" -> ReturnInfo
            returnInfo=ReturnInfo(
                # 第三层：在"备注"中，勾选我们需要的"选项" -> EventInfoFlags
                eventInfo=EventInfoFlags(
                    totalArticleCount=True,
                    socialScore=True
                )
            )
        )

        # 准备基础查询参数，这次我们将正确的"参数套娃"放入'requestedResult'
        query_params = {
            "lang": 'eng',
            "dateStart": datetime.utcnow() - timedelta(hours=24),
            "minArticlesInEvent": 3,
            "requestedResult": requested_result
        }

        if use_whitelist:
            log.info(f"Source whitelist is ENABLED. Filtering by {len(source_names)} trusted sources...")
            source_uris = self.get_uris_for_sources(source_names)
            if not source_uris:
                log.error("No valid source URIs found for the whitelist. Aborting fetch.")
                return []
            # 【核心修复 2】: 根据SDK的警告，使用QueryItems.OR()来明确构造多信源查询
            query_params['sourceUri'] = QueryItems.OR(source_uris)
        else:
            log.info("Source whitelist is DISABLED. Fetching from all sources.")

        # 将构造好的参数字典解包，传入构造函数
        q = QueryEventsIter(**query_params)

        events = list(q.execQuery(self.er, sortBy="size", maxItems=max_events))
        log.info(f"Fetched {len(events)} events.")
        return events

    def fetch_rich_articles_for_event(self, event_uri: str, articles_count: int):
        """获取一个指定事件URI下的、最丰富的文章详情列表。"""
        log.info(f"Fetching up to {articles_count} rich articles for event: {event_uri}")

        # 1. 构造"订单详情"：我们想要什么？
        requested_articles_details = RequestEventArticles(
            count=articles_count,
            sortBy="date",
            returnInfo=ReturnInfo(
                articleInfo=ArticleInfoFlags(
                    sourceInfo=True, concepts=True, sentiment=True, body=True,
                    title=True, url=True, dateTimePub=True
                )
            )
        )

        # 2. 【核心修复】构造"主订单"，并用.setRequestedResult()方法来附加"订单详情"
        q = QueryEvent(event_uri)
        q.setRequestedResult(requested_articles_details)

        # 3. 执行查询：只传入一个查询对象
        result = self.er.execQuery(q)

        # 4. 正确地从返回的嵌套结构中提取文章列表
        if event_uri in result and 'articles' in result[event_uri]:
             articles = result[event_uri]['articles']['results']
             log.info(f"✅ Fetched {len(articles)} articles for event {event_uri}")
             return articles
        else:
             log.warning(f"No articles found for event {event_uri}")
             return []