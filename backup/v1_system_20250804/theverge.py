"""
The Verge 新闻 – EventRegistry sourceUri = 'theverge.com'
"""
from .base_newsapi import BaseNewsAPIScraper

class TheVergeScraper(BaseNewsAPIScraper):
    source = "theverge"

    query = {
        "sourceUri": "theverge.com",
        "count": 50,
        "lang": "eng",
        "sortBy": "date",
    } 