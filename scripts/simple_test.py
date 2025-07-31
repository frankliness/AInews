#!/usr/bin/env python3
"""
简化的 Phoenix 测试脚本
"""

import os
import sys
import logging

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from config.settings import TRUSTED_SOURCES  # 已迁移至 Airflow Variable: TRUSTED_SOURCES_WHITELIST
from scraper.newsapi_client import NewsApiClient

# 配置日志
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def simple_test():
    """简化的测试"""
    try:
        client = NewsApiClient()
        print("✅ NewsApiClient 初始化成功")
        
        # 测试信源URI转换
        test_sources = ["reuters.com", "bbc.com", "nytimes.com"]
        source_uris = client.get_uris_for_sources(test_sources)
        print(f"✅ 成功转换 {len(source_uris)} 个信源URI")
        
        print("🎉 基本功能测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    success = simple_test()
    if not success:
        sys.exit(1) 