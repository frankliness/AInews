"""
El País 新闻 – EventRegistry sourceUri = 'elpais.com'
"""
from .base_newsapi import BaseNewsAPIScraper

class ElPaisScraper(BaseNewsAPIScraper):
    source = "elpais"

    query = {
        "sourceUri": "elpais.com",
        "count": 50,
        "lang": "eng",
        "sortBy": "date",
    } 