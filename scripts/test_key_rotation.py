#!/usr/bin/env python3
"""
测试 API 密钥轮换机制
验证当第一个密钥失败时，是否能正确切换到下一个密钥
"""

import os
import sys
import logging

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.newsapi_client import NewsApiClient
from eventregistry import GetTrendingConcepts

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

def test_key_rotation():
    """测试密钥轮换机制"""
    log.info("🧪 开始测试 API 密钥轮换机制...")
    
    try:
        # 初始化客户端
        client = NewsApiClient()
        log.info("✅ NewsApiClient 初始化成功")
        log.info(f"📊 当前使用密钥索引: {client.current_key_index}")
        
        # 测试 API 调用
        query = GetTrendingConcepts(
            source="news",
            count=5,
            conceptType=["person", "org", "loc"]
        )
        
        log.info("🔍 执行 API 调用...")
        result = client._execute_api_call(client.er.execQuery, query)
        
        log.info("✅ API 调用成功！")
        log.info(f"📊 获取到 {len(result) if isinstance(result, list) else 0} 个概念")
        log.info(f"🔑 最终使用的密钥索引: {client.current_key_index}")
        
        return True
        
    except Exception as e:
        log.error(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    success = test_key_rotation()
    if success:
        print("\n✅ 密钥轮换测试通过！")
    else:
        print("\n❌ 密钥轮换测试失败！")
        sys.exit(1)
