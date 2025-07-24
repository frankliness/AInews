"""
New York Times 新闻 – EventRegistry sourceUri = 'nytimes.com'
"""
from .base_newsapi import BaseNewsAPIScraper

class NYTimesScraper(BaseNewsAPIScraper):
    source = "nytimes"

    query = {
        "sourceUri": "nytimes.com",
        "count": 50,
        "lang": "eng",
        "sortBy": "date",
    } 