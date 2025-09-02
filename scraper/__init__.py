"""
Scraper package – Phoenix V2 系统专用
只保留 Phoenix DAG 实际依赖的模块
"""

# Phoenix 系统实际使用的模块
from .newsapi_client import NewsApiClient  # noqa: F401

# 注意：其他新闻源模块已被标记为冗余，Phoenix 系统不使用
# 如需使用其他模块，请单独导入，不要通过 from scraper import * 的方式
