#!/usr/bin/env python3
"""
深度诊断 EventRegistry 服务问题
检查各种可能的认证和服务问题
"""

import os
import sys
import json
import logging
import requests
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

def test_eventregistry_service_status():
    """测试 EventRegistry 服务状态"""
    log.info("🌐 检查 EventRegistry 服务状态...")
    
    try:
        # 尝试访问 EventRegistry 主页
        response = requests.get("https://eventregistry.org", timeout=10)
        log.info(f"✅ EventRegistry 网站可访问，状态码: {response.status_code}")
        
        # 检查 API 端点
        api_response = requests.get("https://eventregistry.org/api/v1", timeout=10)
        log.info(f"✅ EventRegistry API 端点可访问，状态码: {api_response.status_code}")
        
        return True
    except Exception as e:
        log.error(f"❌ EventRegistry 服务不可访问: {e}")
        return False

def test_api_key_format():
    """测试 API 密钥格式"""
    log.info("🔑 检查 API 密钥格式...")
    
    # 从 notes 文件中获取的 API 密钥
    api_keys = [
        "b03b250a-97ec-4dd0-905e-a038eb1a73e5",
        "b759aed1-f268-405b-90f9-03966227e0bd", 
        "4c0d66ce-07b2-457b-97dc-a08297e61bed",
        "6a9d1a56-f4e4-4627-9ad3-1c5507747f2a"
    ]
    
    for i, key in enumerate(api_keys):
        # 检查密钥格式
        if len(key) == 36 and key.count('-') == 4:
            log.info(f"✅ 密钥 {i+1} 格式正确 (UUID v4)")
        else:
            log.warning(f"⚠️ 密钥 {i+1} 格式可能不正确")
        
        # 检查密钥是否为空或包含特殊字符
        if not key or not key.strip():
            log.error(f"❌ 密钥 {i+1} 为空")
        elif any(c in key for c in [' ', '\t', '\n']):
            log.warning(f"⚠️ 密钥 {i+1} 包含空白字符")
    
    return True

def test_individual_key_authentication():
    """逐个测试 API 密钥的认证状态"""
    log.info("🔐 逐个测试 API 密钥认证...")
    
    api_keys = [
        "b03b250a-97ec-4dd0-905e-a038eb1a73e5",
        "b759aed1-f268-405b-90f9-03966227e0bd", 
        "4c0d66ce-07b2-457b-97dc-a08297e61bed",
        "6a9d1a56-f4e4-4627-9ad3-1c5507747f2a"
    ]
    
    results = []
    
    for i, key in enumerate(api_keys):
        log.info(f"\n--- 测试密钥 {i+1} ---")
        
        try:
            # 初始化客户端
            er = EventRegistry(apiKey=key, allowUseOfArchive=False)
            log.info(f"✅ 密钥 {i+1} 客户端初始化成功")
            
            # 尝试最简单的 API 调用
            from eventregistry import GetTrendingConcepts
            query = GetTrendingConcepts(
                source="news",
                count=1,  # 最小请求
                conceptType=["person"]
            )
            
            result = er.execQuery(query)
            
            if result:
                log.info(f"✅ 密钥 {i+1} API 调用成功")
                results.append({
                    'key_index': i,
                    'key': key[:8] + '...',
                    'status': 'success',
                    'message': 'API 调用成功'
                })
            else:
                log.warning(f"⚠️ 密钥 {i+1} 返回空结果")
                results.append({
                    'key_index': i,
                    'key': key[:8] + '...',
                    'status': 'empty_result',
                    'message': 'API 返回空结果'
                })
                
        except Exception as e:
            error_message = str(e).lower()
            log.error(f"❌ 密钥 {i+1} 失败: {e}")
            
            # 分析错误类型
            if "user is not logged in" in error_message:
                error_type = "authentication_failed"
                error_desc = "用户未登录，认证失败"
            elif "not valid" in error_message or "not recognized" in error_message:
                error_type = "invalid_key"
                error_desc = "API 密钥无效"
            elif "quota" in error_message or "tokens" in error_message:
                error_type = "quota_exceeded"
                error_desc = "配额已用完"
            elif "network" in error_message or "timeout" in error_message:
                error_type = "network_error"
                error_desc = "网络错误"
            else:
                error_type = "unknown_error"
                error_desc = f"未知错误: {str(e)[:100]}"
            
            results.append({
                'key_index': i,
                'key': key[:8] + '...',
                'status': error_type,
                'message': error_desc
            })
    
    return results

def test_network_connectivity():
    """测试网络连接性"""
    log.info("🌍 测试网络连接性...")
    
    try:
        # 测试基本网络连接
        response = requests.get("https://httpbin.org/ip", timeout=5)
        if response.status_code == 200:
            ip_info = response.json()
            log.info(f"✅ 网络连接正常，当前 IP: {ip_info.get('origin', 'unknown')}")
        else:
            log.warning(f"⚠️ 网络连接异常，状态码: {response.status_code}")
            
    except Exception as e:
        log.error(f"❌ 网络连接测试失败: {e}")
        return False
    
    return True

def test_eventregistry_api_endpoints():
    """测试 EventRegistry API 端点"""
    log.info("🔗 测试 EventRegistry API 端点...")
    
    endpoints = [
        "https://eventregistry.org/api/v1",
        "https://eventregistry.org/api/v2",
        "https://eventregistry.org/api"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, timeout=10)
            log.info(f"✅ 端点 {endpoint} 可访问，状态码: {response.status_code}")
        except Exception as e:
            log.warning(f"⚠️ 端点 {endpoint} 不可访问: {e}")
    
    return True

def generate_diagnosis_report(results):
    """生成诊断报告"""
    log.info(f"\n📊 诊断报告汇总:")
    
    # 统计各种状态
    status_counts = {}
    for result in results:
        status = result['status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    log.info(f"🔑 总密钥数量: {len(results)}")
    for status, count in status_counts.items():
        log.info(f"  - {status}: {count}")
    
    # 分析问题
    if all(r['status'] == 'authentication_failed' for r in results):
        log.error(f"\n🚨 严重问题: 所有密钥都出现认证失败！")
        log.error(f"💡 可能原因:")
        log.error(f"   1. EventRegistry 服务端认证机制变化")
        log.error(f"   2. 账户被暂停或需要重新验证")
        log.error(f"   3. IP 地址被限制")
        log.error(f"   4. 服务端临时故障")
        
    elif any(r['status'] == 'authentication_failed' for r in results):
        log.warning(f"\n⚠️ 部分密钥认证失败")
        log.warning(f"💡 建议检查账户状态和密钥有效性")
    
    # 建议
    log.info(f"\n💡 建议行动:")
    log.info(f"   1. 检查 EventRegistry 账户状态")
    log.info(f"   2. 联系 EventRegistry 支持")
    log.info(f"   3. 尝试在 EventRegistry 网站上手动登录")
    log.info(f"   4. 检查是否有 IP 限制")
    log.info(f"   5. 等待服务恢复（如果是临时故障）")

def main():
    """主诊断流程"""
    log.info("🚀 开始深度诊断 EventRegistry 服务...")
    
    # 1. 测试服务状态
    service_ok = test_eventregistry_service_status()
    
    # 2. 测试网络连接
    network_ok = test_network_connectivity()
    
    # 3. 测试 API 端点
    api_ok = test_eventregistry_api_endpoints()
    
    # 4. 测试密钥格式
    format_ok = test_api_key_format()
    
    # 5. 测试密钥认证
    auth_results = test_individual_key_authentication()
    
    # 6. 生成报告
    generate_diagnosis_report(auth_results)
    
    # 7. 总结
    log.info(f"\n🎯 诊断完成！")
    
    if service_ok and network_ok and api_ok:
        log.info("✅ 基础设施正常")
    else:
        log.warning("⚠️ 基础设施存在问题")
    
    if any(r['status'] == 'success' for r in auth_results):
        log.info("✅ 至少有一个密钥工作正常")
    else:
        log.error("❌ 所有密钥都无法使用")
    
    return auth_results

if __name__ == "__main__":
    try:
        results = main()
        
        # 检查是否有成功的密钥
        success_count = sum(1 for r in results if r['status'] == 'success')
        total_count = len(results)
        
        if success_count == 0:
            print(f"\n❌ 诊断完成！所有 {total_count} 个密钥都无法使用")
            print("💡 请立即联系 EventRegistry 支持")
            sys.exit(1)
        else:
            print(f"\n⚠️ 诊断完成！{success_count}/{total_count} 个密钥可用")
            print("💡 建议检查失效密钥的状态")
            
    except Exception as e:
        log.error(f"❌ 诊断过程中发生错误: {e}")
        print(f"\n❌ 诊断失败: {e}")
        sys.exit(1)
