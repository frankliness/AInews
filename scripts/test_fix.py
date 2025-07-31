#!/usr/bin/env python3
"""
测试修复后的 fetch_rich_articles_for_event 方法
"""

import os
import sys
import logging

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def test_fix():
    """测试修复后的方法"""
    try:
        # 直接导入我们的客户端
        from scraper.newsapi_client import NewsApiClient
        
        client = NewsApiClient()
        print("✅ NewsApiClient 初始化成功")
        
        # 测试一个已知的事件URI
        test_event_uri = "eng-10726381"  # 使用之前测试中获取的事件URI
        
        print(f"🔍 测试获取事件 {test_event_uri} 的文章...")
        
        articles = client.fetch_rich_articles_for_event(
            event_uri=test_event_uri,
            articles_count=2
        )
        
        if articles:
            print(f"✅ 成功获取 {len(articles)} 篇文章")
            print("📋 第一篇文章信息:")
            article = articles[0]
            print(f"  - 标题: {article.get('title', 'N/A')}")
            print(f"  - 来源: {article.get('source', {}).get('name', 'N/A')}")
            print(f"  - 发布时间: {article.get('dateTimePub', 'N/A')}")
            return True
        else:
            print("⚠️ 未获取到文章")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_fix()
    if success:
        print("\n🎉 修复验证成功！")
    else:
        print("\n❌ 修复验证失败")
        sys.exit(1) 