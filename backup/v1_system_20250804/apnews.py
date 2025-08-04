"""
Associated Press 新闻 – EventRegistry sourceUri = 'apnews.com'
"""
from .base_newsapi import BaseNewsAPIScraper

class APNewsScraper(BaseNewsAPIScraper):
    source = "apnews"

    query = {
        "sourceUri": "apnews.com",
        "count": 50,
        "lang": "eng",
        "sortBy": "date",
    } 