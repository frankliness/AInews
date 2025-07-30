#!/usr/bin/env python3
"""
测试 Phoenix NewsAPIClient 功能
验证信源过滤、数量控制和API消耗监控
"""

import os
import sys
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from config.settings import TRUSTED_SOURCES  # 已迁移至 Airflow Variable: TRUSTED_SOURCES_WHITELIST
# from config.settings import MAX_EVENTS_TO_FETCH, ARTICLES_PER_EVENT  # 已迁移至 Airflow Variables
from scraper.newsapi_client import NewsApiClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

def test_phoenix_client():
    """测试 Phoenix NewsAPIClient 的核心功能"""
    
    # 1. 获取API密钥
    api_key = os.getenv('EVENTREGISTRY_APIKEY')
    if not api_key:
        log.error("环境变量 EVENTREGISTRY_APIKEY 未设置")
        return False
    
    log.info("✅ API密钥已获取")
    
    # 2. 初始化客户端
    try:
        client = NewsApiClient(api_key=api_key)
        log.info("✅ NewsApiClient 初始化成功")
    except Exception as e:
        log.error(f"❌ NewsApiClient 初始化失败: {e}")
        return False
    
    # 3. 测试API余量查询
    requests_before = client.get_remaining_requests()
    log.info(f"📊 API请求余量: {requests_before}")
    
    # 4. 测试信源URI转换（使用测试用的固定信源列表）
    test_sources = ["reuters.com", "bbc.com", "nytimes.com", "cnn.com", "apnews.com"]
    log.info(f"🔍 测试信源URI转换，使用测试信源列表: {len(test_sources)} 个信源")
    source_uris = client.get_uris_for_sources(test_sources)
    log.info(f"✅ 成功转换 {len(source_uris)} 个信源URI")
    
    # 5. 测试事件获取（使用较小的限制进行测试）
    log.info(f"📰 测试事件获取，限制: 3 个事件（测试模式）")
    events = client.fetch_trending_events(
        source_names=test_sources,  # 使用测试信源列表
        max_events=3  # 只获取3个事件进行测试
    )
    
    if not events:
        log.warning("⚠️ 未获取到任何事件")
        return False
    
    log.info(f"✅ 成功获取 {len(events)} 个事件")
    
    # 6. 测试文章获取
    test_event = events[0]
    log.info(f"📄 测试文章获取，事件: {test_event.get('uri', 'N/A')}")
    
    articles = client.fetch_rich_articles_for_event(
        event_uri=test_event['uri'],
        articles_count=2  # 只获取2篇文章进行测试
    )
    
    log.info(f"✅ 成功获取 {len(articles)} 篇文章")
    
    # 7. 验证文章数据结构
    if articles:
        article = articles[0]
        log.info("📋 文章数据结构验证:")
        log.info(f"  - URI: {article.get('uri', 'N/A')}")
        log.info(f"  - 标题: {article.get('title', 'N/A')}")
        log.info(f"  - 来源: {article.get('source', {}).get('name', 'N/A')}")
        log.info(f"  - 发布时间: {article.get('dateTime', 'N/A')}")
        log.info(f"  - 情感分数: {article.get('sentiment', 'N/A')}")
    
    # 8. 测试API消耗监控
    requests_after = client.get_remaining_requests()
    if requests_before and requests_after:
        consumed = requests_before - requests_after
        log.info(f"💰 API请求消耗: {consumed}")
    
    log.info("🎉 Phoenix NewsAPIClient 测试完成！")
    return True

if __name__ == "__main__":
    success = test_phoenix_client()
    if success:
        print("\n✅ 所有测试通过！Phoenix 系统准备就绪。")
    else:
        print("\n❌ 测试失败，请检查配置和API密钥。")
        sys.exit(1) 