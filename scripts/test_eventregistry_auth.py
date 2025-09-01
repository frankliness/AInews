#!/usr/bin/env python3
"""
测试 EventRegistry API 密钥认证状态
验证 API 密钥是否有效，以及客户端是否能正确登录
"""

import os
import sys
import json
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eventregistry import EventRegistry, GetTrendingConcepts

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

def test_api_key(api_key: str):
    """测试单个 API 密钥"""
    log.info(f"🔑 测试 API 密钥: {api_key[:8]}...")
    
    try:
        # 初始化客户端
        er = EventRegistry(apiKey=api_key, allowUseOfArchive=False)
        log.info("✅ EventRegistry 客户端初始化成功")
        
        # 测试简单的 API 调用
        log.info("🧪 测试 API 连接...")
        query = GetTrendingConcepts(
            source="news",
            count=5,  # 只获取5个概念进行测试
            conceptType=["person", "org", "loc"]
        )
        
        result = er.execQuery(query)
        log.info("✅ API 调用成功！")
        log.info(f"📊 获取到 {len(result) if isinstance(result, list) else 0} 个概念")
        
        return True
        
    except Exception as e:
        log.error(f"❌ API 密钥测试失败: {e}")
        return False

def test_all_keys():
    """测试所有配置的 API 密钥"""
    
    # 从环境变量或配置文件获取 API 密钥
    # 这里使用 notes 文件中提到的密钥进行测试
    test_keys = [
        "b03b250a-97ec-4dd0-905e-a038eb1a73e5",
        "b759aed1-f268-405b-90f9-03966227e0bd", 
        "4c0d66ce-07b2-457b-97dc-a08297e61bed",
        "6a9d1a56-f4e4-4627-9ad3-1c5507747f2a"
    ]
    
    log.info(f"🔍 开始测试 {len(test_keys)} 个 API 密钥...")
    
    working_keys = []
    failed_keys = []
    
    for i, key in enumerate(test_keys, 1):
        log.info(f"\n--- 测试密钥 {i}/{len(test_keys)} ---")
        if test_api_key(key):
            working_keys.append(key)
        else:
            failed_keys.append(key)
    
    # 输出测试结果
    log.info(f"\n📋 测试结果汇总:")
    log.info(f"✅ 有效的密钥: {len(working_keys)}/{len(test_keys)}")
    log.info(f"❌ 无效的密钥: {len(failed_keys)}/{len(test_keys)}")
    
    if working_keys:
        log.info("🎉 发现有效的 API 密钥:")
        for key in working_keys:
            log.info(f"  - {key[:8]}...")
    
    if failed_keys:
        log.warning("⚠️ 以下密钥无效或已过期:")
        for key in failed_keys:
            log.warning(f"  - {key[:8]}...")
    
    return len(working_keys) > 0

def test_airflow_variable_simulation():
    """模拟 Airflow Variable 中的 API 密钥配置"""
    log.info("\n🔧 模拟 Airflow Variable 配置...")
    
    # 模拟从 Airflow Variable 获取的配置
    keys_json_str = '{"keys": ["b03b250a-97ec-4dd0-905e-a038eb1a73e5", "b759aed1-f268-405b-90f9-03966227e0bd", "4c0d66ce-07b2-457b-97dc-a08297e61bed", "6a9d1a56-f4e4-4627-9ad3-1c5507747f2a"]}'
    
    try:
        config = json.loads(keys_json_str)
        api_keys = config.get("keys", [])
        log.info(f"📝 解析配置成功，找到 {len(api_keys)} 个密钥")
        
        # 测试第一个密钥
        if api_keys:
            first_key = api_keys[0]
            log.info(f"🧪 测试第一个密钥: {first_key[:8]}...")
            if test_api_key(first_key):
                log.info("✅ 第一个密钥测试通过")
            else:
                log.warning("⚠️ 第一个密钥测试失败")
        
    except Exception as e:
        log.error(f"❌ 配置解析失败: {e}")

if __name__ == "__main__":
    log.info("🚀 开始 EventRegistry API 认证测试...")
    
    # 测试所有密钥
    success = test_all_keys()
    
    # 模拟 Airflow Variable 配置
    test_airflow_variable_simulation()
    
    if success:
        print("\n✅ 测试完成！发现有效的 API 密钥。")
    else:
        print("\n❌ 测试完成！所有 API 密钥都无效。")
        print("💡 建议检查:")
        print("  1. API 密钥是否正确")
        print("  2. 密钥是否已过期")
        print("  3. 账户是否有足够的权限")
        print("  4. EventRegistry 服务是否正常")
        sys.exit(1)
