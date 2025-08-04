# 文件路径: scraper/newsapi_client.py (最终版)

import logging
import json
import random
from datetime import datetime, timedelta
from airflow.models import Variable
from eventregistry import (
    EventRegistry,
    QueryEventsIter,
    QueryEvent,
    RequestEventArticles,
    ReturnInfo,
    ArticleInfoFlags,
    EventInfoFlags,
    RequestEventsInfo,
    QueryItems,
    SourceInfoFlags
)

log = logging.getLogger(__name__)

class NewsApiClient:
    def __init__(self):
        """
        Initializes the client by loading a pool of API keys from Airflow Variables
        and selecting one to start with.
        """
        keys_json_str = Variable.get("ainews_eventregistry_apikeys", default_var='{"keys":[]}')
        self.api_keys = json.loads(keys_json_str).get("keys", [])
        if not self.api_keys:
            raise ValueError("No EventRegistry API keys found in Airflow Variable 'ainews_eventregistry_apikeys'.")
        
        # 从列表的随机位置开始，以避免每次都从第一个key开始消耗
        random.shuffle(self.api_keys)
        self.current_key_index = 0
        self.source_uri_cache = {}
        self._initialize_er_client()

    def _initialize_er_client(self):
        """Initializes the EventRegistry client with the current key."""
        current_key = self.api_keys[self.current_key_index]
        log.info(f"Initializing EventRegistry client with key index: {self.current_key_index}")
        self.er = EventRegistry(apiKey=current_key, allowUseOfArchive=False)

    def _rotate_key(self):
        """Rotates to the next API key in the list."""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        log.info(f"Rotating to next API key. New index: {self.current_key_index}")
        self._initialize_er_client()
        # 如果所有key都轮换了一遍，说明可能都已失效，抛出异常
        if self.current_key_index == 0:
            raise Exception("All API keys have been tried and failed. Please check their status.")

    def _execute_api_call(self, func, *args, **kwargs):
        """
        Executes an API call with automatic key rotation on failure.
        `func` is the EventRegistry client method to call.
        """
        max_retries = len(self.api_keys)
        for attempt in range(max_retries):
            try:
                # 执行实际的API调用
                return func(*args, **kwargs)
            except Exception as e:
                # 检查错误信息是否与配额相关
                error_message = str(e).lower()
                if ("daily access quota" in error_message or 
                    "not valid" in error_message or 
                    "quota" in error_message or
                    "not recognized as a valid key" in error_message):
                    log.info(f"API Key at index {self.current_key_index} failed due to quota/validation error: {e}")
                    self._rotate_key()
                    # 继续下一次循环，使用新的key重试
                    continue 
                else:
                    # 如果是其他类型的错误，直接抛出
                    raise e
        # 如果循环结束仍未成功，说明所有key都已尝试失败
        raise Exception("All API keys failed. Unable to complete the API call.")

    def get_source_uri(self, source_name: str):
        if source_name in self.source_uri_cache:
            return self.source_uri_cache[source_name]
        try:
            uri = self._execute_api_call(self.er.getSourceUri, source_name)
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

    def fetch_trending_events(self, source_names: list[str], max_events: int, use_whitelist: bool = True, sort_by: str = "size", date_start: datetime | None = None):
        """获取热门事件，并根据开关决定是否启用信源白名单过滤。
        
        Args:
            source_names: 信源名称列表
            max_events: 最大事件数量
            use_whitelist: 是否使用白名单过滤
            sort_by: 排序方式，"size"表示按热门程度，"date"表示按时间
            date_start: 开始时间，仅在sort_by="date"时使用
        """
        log.info(f"Fetching up to {max_events} trending events with sort_by={sort_by}...")

        # 【核心修复】: 将所有参数"平铺"开来，作为独立的关键字参数传递
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
            "minArticlesInEvent": 3,
            "requestedResult": requested_result
        }

        # 根据排序方式设置不同的时间范围
        if sort_by == "date" and date_start:
            query_params["dateStart"] = date_start
            log.info(f"Using custom date_start: {date_start}")
        else:
            query_params["dateStart"] = datetime.utcnow() - timedelta(hours=24)

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

        events = list(self._execute_api_call(q.execQuery, self.er, sortBy=sort_by, maxItems=max_events))
        log.info(f"Fetched {len(events)} events with sort_by={sort_by}.")
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
                    title=True, url=True, image=True, date=True
                ),
                sourceInfo=SourceInfoFlags(ranking=True)
            )
        )

        # 2. 构造"查询订单"：我们要查什么？
        query = QueryEvent(event_uri)

        # 3. 执行查询：设置请求参数并执行
        query.setRequestedResult(requested_articles_details)
        result = self._execute_api_call(self.er.execQuery, query)
        
        # 4. 从嵌套结构中提取文章列表
        if event_uri in result and 'articles' in result[event_uri]:
            articles = result[event_uri]['articles']['results']
            log.info(f"Fetched {len(articles)} articles for event {event_uri}.")
            return articles
        else:
            log.warning(f"No articles found for event {event_uri}")
            return []