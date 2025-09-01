#!/usr/bin/env python3
"""
EventRegistry API 配额监控脚本
用于独立监控和检查API配额状态
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scraper.newsapi_client import NewsApiClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

def main():
    """主函数：检查API配额状态"""
    try:
        # 初始化客户端
        log.info("正在初始化 EventRegistry 客户端...")
        client = NewsApiClient()
        
        # 检查配额状态
        log.info("正在检查API配额状态...")
        quota_status = client.check_api_quota()
        
        # 输出配额信息
        print("\n" + "="*50)
        print("EventRegistry API 配额状态报告")
        print("="*50)
        print(f"状态: {quota_status['status']}")
        print(f"剩余配额: {quota_status['remaining']}")
        
        if 'error' in quota_status:
            print(f"错误: {quota_status['error']}")
        elif 'warning' in quota_status:
            print(f"警告: {quota_status['warning']}")
        elif 'info' in quota_status:
            print(f"信息: {quota_status['info']}")
        
        print(f"是否可以继续: {'是' if quota_status['can_proceed'] else '否'}")
        print("="*50)
        
        # 获取详细的配额信息
        try:
            remaining = client.er.getRemainingAvailableRequests()
            print(f"原始配额信息: {remaining}")
        except Exception as e:
            print(f"获取原始配额信息失败: {e}")
        
        # 根据配额状态给出建议
        if not quota_status['can_proceed']:
            print("\n❌ 建议: 停止所有API调用，等待配额重置或升级到付费计划")
        elif quota_status['status'] == 'low':
            print("\n⚠️  建议: 减少API调用频率，监控配额使用情况")
        elif quota_status['status'] == 'critical':
            print("\n🚨 建议: 立即停止非必要的API调用")
        else:
            print("\n✅ 配额状态正常，可以继续使用")
            
    except Exception as e:
        log.error(f"配额检查失败: {e}")
        print(f"\n❌ 配额检查失败: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
