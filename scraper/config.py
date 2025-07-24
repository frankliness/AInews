"""
Twitter 抓取配置管理模块
支持配额平均分配和活跃度过滤的配置项
"""
import os
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class TwitterConfig:
    """Twitter 抓取配置"""
    # 配额管理
    safety_margin: int = 5  # 安全余量，避免越界
    max_pages_per_user: int = 5  # 每用户最大页数
    
    # 活跃度过滤
    active_window_days: int = 7  # 活跃窗口天数
    min_tweets_24h: int = 1  # 24小时内最小推文数
    min_tweets_7d: int = 5  # 7天内最小推文数
    inactive_skip_rounds: int = 4  # 连续不活跃轮数告警
    
    # API 配置
    max_results_per_request: int = 100  # 单次请求最大结果数
    
    # 缓存配置
    user_id_cache_table: str = "twitter_users"  # 用户ID缓存表名
    
    @classmethod
    def from_env(cls) -> 'TwitterConfig':
        """从环境变量加载配置"""
        return cls(
            safety_margin=int(os.getenv('SAFETY_MARGIN', '5')),
            max_pages_per_user=int(os.getenv('MAX_PAGES_PER_USER', '5')),
            active_window_days=int(os.getenv('ACTIVE_WINDOW_DAYS', '7')),
            min_tweets_24h=int(os.getenv('MIN_TWEETS_24H', '1')),
            min_tweets_7d=int(os.getenv('MIN_TWEETS_7D', '5')),
            inactive_skip_rounds=int(os.getenv('INACTIVE_SKIP_ROUNDS', '4')),
            max_results_per_request=int(os.getenv('MAX_RESULTS_PER_REQUEST', '100')),
            user_id_cache_table=os.getenv('USER_ID_CACHE_TABLE', 'twitter_users'),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'safety_margin': self.safety_margin,
            'max_pages_per_user': self.max_pages_per_user,
            'active_window_days': self.active_window_days,
            'min_tweets_24h': self.min_tweets_24h,
            'min_tweets_7d': self.min_tweets_7d,
            'inactive_skip_rounds': self.inactive_skip_rounds,
            'max_results_per_request': self.max_results_per_request,
            'user_id_cache_table': self.user_id_cache_table,
        }

# 全局配置实例
config = TwitterConfig.from_env() 