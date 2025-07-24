"""
Financial Times 新闻 – EventRegistry sourceUri = 'ft.com'
"""
from .base_newsapi import BaseNewsAPIScraper

class FTScraper(BaseNewsAPIScraper):
    source = "ft"

    query = {
        "sourceUri": "ft.com",
        "count": 50,
        "lang": "eng",
        "sortBy": "date",
    } 