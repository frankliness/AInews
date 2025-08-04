"""
BBC World 新闻 – 同样用 EventRegistry，限制语言为英语 (lang='eng')
"""
from .base_newsapi import BaseNewsAPIScraper

class BBCScraper(BaseNewsAPIScraper):
    source = "bbc"

    query = {
        "sourceUri": "bbc.com",
        "count": 50,
        "lang":  "eng",
        "sortBy": "date",
    }
