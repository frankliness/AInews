#!/usr/bin/env python3
"""
监控 EventRegistry API 配额使用情况
检查所有配置的 API 密钥的配额状态
"""

import os
import sys
import json
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eventregistry import EventRegistry

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

def check_api_key_quota(api_key: str, key_index: int):
    """检查单个 API 密钥的配额状态"""
    log.info(f"🔑 检查密钥 {key_index + 1}: {api_key[:8]}...")
    
    try:
        # 初始化客户端
        er = EventRegistry(apiKey=api_key, allowUseOfArchive=False)
        
        # 尝试一个简单的 API 调用来检查配额
        # 使用最小的请求来节省配额
        from eventregistry import GetTrendingConcepts
        query = GetTrendingConcepts(
            source="news",
            count=1,  # 只获取1个概念来测试
            conceptType=["person"]
        )
        
        result = er.execQuery(query)
        
        if result:
            log.info(f"✅ 密钥 {key_index + 1} 工作正常，配额充足")
            return {
                'key_index': key_index,
                'key': api_key[:8] + '...',
                'status': 'active',
                'quota': 'sufficient',
                'message': 'API 调用成功'
            }
        else:
            log.warning(f"⚠️ 密钥 {key_index + 1} 返回空结果")
            return {
                'key_index': key_index,
                'key': api_key[:8] + '...',
                'status': 'warning',
                'quota': 'unknown',
                'message': 'API 返回空结果'
            }
            
    except Exception as e:
        error_message = str(e).lower()
        
        if "used all available tokens for unsubscribed users" in error_message:
            log.error(f"❌ 密钥 {key_index + 1} 配额已用完，需要付费订阅")
            return {
                'key_index': key_index,
                'key': api_key[:8] + '...',
                'status': 'exhausted',
                'quota': 'exhausted',
                'message': '免费用户配额已用完，需要付费订阅'
            }
        elif "daily access quota" in error_message or "quota" in error_message:
            log.error(f"❌ 密钥 {key_index + 1} 达到每日配额限制")
            return {
                'key_index': key_index,
                'key': api_key[:8] + '...',
                'status': 'quota_exceeded',
                'quota': 'daily_limit_reached',
                'message': '达到每日配额限制'
            }
        elif "not valid" in error_message or "not recognized" in error_message:
            log.error(f"❌ 密钥 {key_index + 1} 无效或已过期")
            return {
                'key_index': key_index,
                'key': api_key[:8] + '...',
                'status': 'invalid',
                'quota': 'n/a',
                'message': 'API 密钥无效或已过期'
            }
        else:
            log.error(f"❌ 密钥 {key_index + 1} 遇到未知错误: {e}")
            return {
                'key_index': key_index,
                'key': api_key[:8] + '...',
                'status': 'error',
                'quota': 'unknown',
                'message': f'未知错误: {str(e)[:100]}'
            }

def monitor_all_keys():
    """监控所有配置的 API 密钥"""
    
    # 从 notes 文件中获取的 API 密钥
    api_keys = [
        "b03b250a-97ec-4dd0-905e-a038eb1a73e5",
        "b759aed1-f268-405b-90f9-03966227e0bd", 
        "4c0d66ce-07b2-457b-97dc-a08297e61bed",
        "6a9d1a56-f4e4-4627-9ad3-1c5507747f2a"
    ]
    
    log.info(f"🔍 开始监控 {len(api_keys)} 个 EventRegistry API 密钥...")
    
    results = []
    active_keys = 0
    exhausted_keys = 0
    invalid_keys = 0
    
    for i, key in enumerate(api_keys):
        result = check_api_key_quota(key, i)
        results.append(result)
        
        if result['status'] == 'active':
            active_keys += 1
        elif result['status'] == 'exhausted':
            exhausted_keys += 1
        elif result['status'] == 'invalid':
            invalid_keys += 1
    
    # 输出监控结果
    log.info(f"\n📊 配额监控结果汇总:")
    log.info(f"🔑 总密钥数量: {len(api_keys)}")
    log.info(f"✅ 工作正常的密钥: {active_keys}")
    log.info(f"❌ 配额耗尽的密钥: {exhausted_keys}")
    log.info(f"⚠️ 无效的密钥: {invalid_keys}")
    
    # 详细状态报告
    log.info(f"\n📋 详细状态报告:")
    for result in results:
        status_emoji = {
            'active': '✅',
            'exhausted': '❌',
            'quota_exceeded': '⚠️',
            'invalid': '🚫',
            'error': '❓',
            'warning': '⚠️'
        }
        
        emoji = status_emoji.get(result['status'], '❓')
        log.info(f"{emoji} 密钥 {result['key_index'] + 1} ({result['key']}): {result['message']}")
    
    # 建议和警告
    if active_keys == 0:
        log.error(f"\n🚨 严重警告: 所有 API 密钥都无法使用！")
        log.error(f"💡 建议立即:")
        log.error(f"   1. 联系 EventRegistry 升级到付费计划")
        log.error(f"   2. 申请新的 API 密钥")
        log.error(f"   3. 检查账户状态和配额限制")
    elif active_keys < len(api_keys) / 2:
        log.warning(f"\n⚠️ 警告: 超过一半的 API 密钥无法使用")
        log.warning(f"💡 建议尽快处理配额问题")
    
    if exhausted_keys > 0:
        log.info(f"\n💡 对于配额耗尽的密钥:")
        log.info(f"   1. 检查 EventRegistry 账户状态")
        log.info(f"   2. 考虑升级到付费计划")
        log.info(f"   3. 申请新的 API 密钥")
    
    return results

if __name__ == "__main__":
    log.info("🚀 开始 EventRegistry API 配额监控...")
    
    try:
        results = monitor_all_keys()
        
        # 生成摘要报告
        active_count = sum(1 for r in results if r['status'] == 'active')
        total_count = len(results)
        
        if active_count == 0:
            print(f"\n❌ 监控完成！所有 {total_count} 个 API 密钥都无法使用")
            print("💡 请立即处理配额问题")
            sys.exit(1)
        elif active_count < total_count:
            print(f"\n⚠️ 监控完成！{active_count}/{total_count} 个 API 密钥可用")
            print("💡 建议尽快处理配额问题")
        else:
            print(f"\n✅ 监控完成！所有 {total_count} 个 API 密钥都工作正常")
            
    except Exception as e:
        log.error(f"❌ 监控过程中发生错误: {e}")
        print(f"\n❌ 监控失败: {e}")
        sys.exit(1)
