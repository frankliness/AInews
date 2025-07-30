#!/usr/bin/env python3
"""
简化的 Phoenix 测试脚本
"""

import os
import sys
import logging

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import TRUSTED_SOURCES
from scraper.newsapi_client import NewsApiClient

# 配置日志
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def simple_test():
    """简化的测试"""
    api_key = os.getenv('EVENTREGISTRY_APIKEY')
    if not api_key:
        print("❌ API密钥未设置")
        return False
    
    try:
        client = NewsApiClient(api_key=api_key)
        print("✅ NewsApiClient 初始化成功")
        
        # 测试信源URI转换
        source_uris = client.get_uris_for_sources(TRUSTED_SOURCES[:3])
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