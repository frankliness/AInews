"""
Bloomberg 新闻 – EventRegistry sourceUri = 'bloomberg.com'
"""
from .base_newsapi import BaseNewsAPIScraper

class BloombergScraper(BaseNewsAPIScraper):
    source = "bloomberg"

    query = {
        "sourceUri": "bloomberg.com",
        "count": 50,
        "lang": "eng",
        "sortBy": "date",
    } 