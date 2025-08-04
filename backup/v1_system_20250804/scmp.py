"""
South China Morning Post 新闻 – EventRegistry sourceUri = 'scmp.com'
"""
from .base_newsapi import BaseNewsAPIScraper

class SCMPScraper(BaseNewsAPIScraper):
    source = "scmp"

    query = {
        "sourceUri": "scmp.com",
        "count": 50,
        "lang": "eng",
        "sortBy": "date",
    } 