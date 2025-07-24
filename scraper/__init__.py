"""
Scraper package – export常用类方便外部直接导入：
    from scraper import ReutersScraper, BBCScraper, TwitterScraper, NYTimesScraper, etc.
"""

from .reuters import ReutersScraper  # noqa: F401
from .bbc import BBCScraper          # noqa: F401
from .twitter_source import TwitterScraper  # noqa: F401

# 新增的新闻源抓取器
from .nytimes import NYTimesScraper  # noqa: F401
from .apnews import APNewsScraper  # noqa: F401
from .bloomberg import BloombergScraper  # noqa: F401
from .theguardian import TheGuardianScraper  # noqa: F401
from .cnn import CNNScraper  # noqa: F401
from .ft import FTScraper  # noqa: F401
from .skynews import SkyNewsScraper  # noqa: F401
from .elpais import ElPaisScraper  # noqa: F401
from .scmp import SCMPScraper  # noqa: F401
from .aljazeera import AlJazeeraScraper  # noqa: F401
from .theverge import TheVergeScraper  # noqa: F401
