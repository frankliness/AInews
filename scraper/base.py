from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Iterable, Optional
import logging

log = logging.getLogger(__name__)

@dataclass
class ScrapedItem:
    source: str                # 'reuters' / 'bbc' / 'twitter'
    title: str
    body: str
    published_at: datetime
    url: str
    likes: int = 0
    retweets: int = 0          # or "reposts" on X
    
    # EventRegistry相关字段
    event_id: Optional[str] = None
    embedding: Optional[str] = None
    total_articles_24h: Optional[int] = None
    source_importance: Optional[int] = None
    weight: Optional[int] = None
    sentiment: Optional[float] = None

    # 便于直接传给 psycopg2.execute(**dict)
    def as_dict(self) -> Dict[str, Any]:
        return self.__dict__


class BaseScraper:
    """所有 Scraper 的抽象基类（可选实现 __iter__ / fetch / parse）"""

    source: str = "base"

    def fetch(self):
        """抓取原始数据 – 子类实现"""
        raise NotImplementedError

    def parse(self, raw, db_connection=None) -> Iterable[ScrapedItem]:
        """把 raw 解析为 ScrapedItem 迭代器 – 子类实现"""
        raise NotImplementedError

    def run(self, db_connection=None):
        """运行抓取流程"""
        try:
            raw_data = self.fetch()
            for item in self.parse(raw_data, db_connection):
                yield item
        except Exception as e:
            log.error(f"抓取失败 {self.source}: {e}")
            raise
