"""
Reuters 最新新闻（英文）– EventRegistry 已内置 sourceUri = 'reuters.com'
"""
from .base_newsapi import BaseNewsAPIScraper

class ReutersScraper(BaseNewsAPIScraper):
    source = "reuters"

    # 取最近 50 条即可；免费版一次性最大 50
    query = {
        "sourceUri": "reuters.com",
        "count": 50,
        "sortBy": "date",
    }
