"""
The Guardian 新闻 – EventRegistry sourceUri = 'theguardian.com'
"""
from .base_newsapi import BaseNewsAPIScraper

class TheGuardianScraper(BaseNewsAPIScraper):
    source = "theguardian"

    query = {
        "sourceUri": "theguardian.com",
        "count": 50,
        "lang": "eng",
        "sortBy": "date",
    } 