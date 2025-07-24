"""
CNN 新闻 – EventRegistry sourceUri = 'cnn.com'
"""
from .base_newsapi import BaseNewsAPIScraper

class CNNScraper(BaseNewsAPIScraper):
    source = "cnn"

    query = {
        "sourceUri": "cnn.com",
        "count": 50,
        "lang": "eng",
        "sortBy": "date",
    } 