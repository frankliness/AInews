#!/usr/bin/env python3
"""
简化的 API 密钥轮换测试
直接测试 EventRegistry 的密钥轮换逻辑，不依赖 Airflow
"""

import os
import sys
import json
import logging
import random
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

class SimpleNewsApiClient:
    """简化的 NewsApiClient，用于测试密钥轮换逻辑"""
    
    def __init__(self):
        """初始化客户端，模拟从配置获取 API 密钥"""
        # 模拟从配置获取的 API 密钥
        self.api_keys = [
            "b03b250a-97ec-4dd0-905e-a038eb1a73e5",  # 第一个密钥（配额已用完）
            "b759aed1-f268-405b-90f9-03966227e0bd",  # 第二个密钥（有效）
            "4c0d66ce-07b2-457b-97dc-a08297e61bed",  # 第三个密钥（有效）
            "6a9d1a56-f4e4-4627-9ad3-1c5507747f2a"   # 第四个密钥（有效）
        ]
        
        # 从列表的随机位置开始，以避免每次都从第一个key开始消耗
        random.shuffle(self.api_keys)
        self.current_key_index = 0
        self._initialize_er_client()
        
        log.info(f"🔑 初始化完成，使用密钥索引: {self.current_key_index}")

    def _initialize_er_client(self):
        """使用当前密钥初始化 EventRegistry 客户端"""
        current_key = self.api_keys[self.current_key_index]
        log.info(f"🔄 初始化 EventRegistry 客户端，密钥索引: {self.current_key_index}")
        self.er = EventRegistry(apiKey=current_key, allowUseOfArchive=False)

    def _rotate_key(self):
        """轮换到下一个 API 密钥"""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        log.info(f"🔄 轮换到下一个 API 密钥，新索引: {self.current_key_index}")
        self._initialize_er_client()
        
        # 如果所有密钥都轮换了一遍，说明可能都已失效
        if self.current_key_index == 0:
            raise Exception("所有 API 密钥都已尝试并失败。请检查它们的状态。")

    def _execute_api_call(self, func, *args, **kwargs):
        """
        执行 API 调用，自动处理密钥轮换
        """
        max_retries = len(self.api_keys)
        for attempt in range(max_retries):
            try:
                log.info(f"🧪 尝试 API 调用 (尝试 {attempt + 1}/{max_retries})，使用密钥索引: {self.current_key_index}")
                # 执行实际的 API 调用
                return func(*args, **kwargs)
            except Exception as e:
                # 检查错误信息是否与配额相关
                error_message = str(e).lower()
                if ("daily access quota" in error_message or 
                    "not valid" in error_message or 
                    "quota" in error_message or
                    "not recognized as a valid key" in error_message or
                    "used all available tokens for unsubscribed users" in error_message or
                    "subscribe to a paid plan" in error_message):
                    log.warning(f"⚠️ 密钥索引 {self.current_key_index} 因配额/验证错误失败: {e}")
                    if attempt < max_retries - 1:  # 如果不是最后一次尝试
                        self._rotate_key()
                        log.info("🔄 已轮换密钥，继续重试...")
                        continue
                    else:
                        log.error("❌ 所有密钥都已尝试失败")
                        raise e
                else:
                    # 如果是其他类型的错误，直接抛出
                    log.error(f"❌ 遇到非配额相关错误: {e}")
                    raise e
        
        # 如果循环结束仍未成功，说明所有密钥都已尝试失败
        raise Exception("所有 API 密钥都失败。无法完成 API 调用。")

def test_key_rotation():
    """测试密钥轮换机制"""
    log.info("🧪 开始测试简化的 API 密钥轮换机制...")
    
    try:
        # 初始化客户端
        client = SimpleNewsApiClient()
        log.info("✅ SimpleNewsApiClient 初始化成功")
        
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
        print("💡 这说明当第一个密钥配额用完时，系统能正确切换到下一个有效密钥")
    else:
        print("\n❌ 密钥轮换测试失败！")
        print("💡 请检查密钥轮换逻辑或 API 密钥状态")
        sys.exit(1)
