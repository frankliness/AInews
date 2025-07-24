"""
Sky News 新闻 – EventRegistry sourceUri = 'news.sky.com'
"""
from .base_newsapi import BaseNewsAPIScraper

class SkyNewsScraper(BaseNewsAPIScraper):
    source = "skynews"

    query = {
        "sourceUri": "news.sky.com",
        "count": 50,
        "lang": "eng",
        "sortBy": "date",
    } 