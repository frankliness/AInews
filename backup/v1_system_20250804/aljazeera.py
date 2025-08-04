"""
Al Jazeera 新闻 – EventRegistry sourceUri = 'aljazeera.com'
"""
from .base_newsapi import BaseNewsAPIScraper

class AlJazeeraScraper(BaseNewsAPIScraper):
    source = "aljazeera"

    query = {
        "sourceUri": "aljazeera.com",
        "count": 50,
        "lang": "eng",
        "sortBy": "date",
    } 