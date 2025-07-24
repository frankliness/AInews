"""
Prometheus 指标管理器
实现Twitter抓取的全链路可观测性
"""
import logging
from typing import Dict, Optional
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# 尝试导入prometheus_client，如果不存在则使用模拟实现
try:
    from prometheus_client import Gauge, Counter, Histogram
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # 模拟实现
    class MockMetric:
        def __init__(self, name, description, **kwargs):
            self.name = name
            self.description = description
            self._value = 0
        
        def labels(self, **kwargs):
            return self
        
        def set(self, value, **kwargs):
            self._value = value
        
        def inc(self, value=1, **kwargs):
            self._value += value
        
        def observe(self, value):
            self._value = value
    
    Gauge = Counter = Histogram = MockMetric

log = logging.getLogger(__name__)

class TwitterMetrics:
    """Twitter抓取指标管理器"""
    
    def __init__(self):
        if PROMETHEUS_AVAILABLE:
            self._init_prometheus_metrics()
        else:
            self._init_mock_metrics()
    
    def _init_prometheus_metrics(self):
        """初始化Prometheus指标"""
        # 配额分配指标
        self.quota_assigned = Gauge(
            'twitter_quota_assigned',
            '本窗口为该用户分配的页数',
            ['username']
        )
        
        # 配额使用指标
        self.quota_used = Counter(
            'twitter_quota_used',
            '已消耗页数',
            ['username', 'window']
        )
        
        # 限速指标
        self.rate_limit_total = Counter(
            'twitter_rate_limit_total',
            '端点触发 429/403 次数',
            ['endpoint']
        )
        
        # 窗口耗尽指标
        self.window_exhausted_total = Counter(
            'twitter_window_exhausted_total',
            '提前耗光窗口的次数'
        )
        
        # 用户缓存指标
        self.user_cache_hits = Counter(
            'twitter_user_cache_hits_total',
            '用户ID缓存命中次数'
        )
        
        self.user_cache_misses = Counter(
            'twitter_user_cache_misses_total',
            '用户ID缓存未命中次数'
        )
        
        # 活跃度过滤指标
        self.active_users_total = Gauge(
            'twitter_active_users_total',
            '活跃用户总数'
        )
        
        self.inactive_users_total = Gauge(
            'twitter_inactive_users_total',
            '不活跃用户总数'
        )
        
        # 抓取性能指标
        self.fetch_duration = Histogram(
            'twitter_fetch_duration_seconds',
            '抓取耗时（秒）',
            ['username']
        )
        
        self.tweets_fetched = Counter(
            'twitter_tweets_fetched_total',
            '抓取推文总数',
            ['username']
        )
    
    def _init_mock_metrics(self):
        """初始化模拟指标（用于测试）"""
        self.quota_assigned = MockMetric('twitter_quota_assigned', '配额分配')
        self.quota_used = MockMetric('twitter_quota_used', '配额使用')
        self.rate_limit_total = MockMetric('twitter_rate_limit_total', '限速次数')
        self.window_exhausted_total = MockMetric('twitter_window_exhausted_total', '窗口耗尽')
        self.user_cache_hits = MockMetric('twitter_user_cache_hits_total', '缓存命中')
        self.user_cache_misses = MockMetric('twitter_user_cache_misses_total', '缓存未命中')
        self.active_users_total = MockMetric('twitter_active_users_total', '活跃用户数')
        self.inactive_users_total = MockMetric('twitter_inactive_users_total', '不活跃用户数')
        self.fetch_duration = MockMetric('twitter_fetch_duration_seconds', '抓取耗时')
        self.tweets_fetched = MockMetric('twitter_tweets_fetched_total', '推文总数')
    
    def record_quota_assigned(self, username: str, quota: int):
        """记录配额分配"""
        self.quota_assigned.labels(username=username).set(quota)
        log.info(f"记录配额分配: {username} = {quota}")
    
    def record_quota_used(self, username: str, used: int, window: str = None):
        """记录配额使用"""
        if window is None:
            window = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d_%H")
        
        self.quota_used.labels(username=username, window=window).inc(used)
        log.debug(f"记录配额使用: {username} +{used} (窗口: {window})")
    
    def record_rate_limit(self, endpoint: str):
        """记录限速事件"""
        self.rate_limit_total.labels(endpoint=endpoint).inc()
        log.warning(f"记录限速事件: {endpoint}")
    
    def record_window_exhausted(self):
        """记录窗口耗尽"""
        self.window_exhausted_total.inc()
        log.warning("记录窗口耗尽事件")
    
    def record_cache_hit(self):
        """记录缓存命中"""
        self.user_cache_hits.inc()
        log.debug("记录缓存命中")
    
    def record_cache_miss(self):
        """记录缓存未命中"""
        self.user_cache_misses.inc()
        log.debug("记录缓存未命中")
    
    def record_active_users(self, active_count: int, inactive_count: int):
        """记录活跃用户统计"""
        self.active_users_total.set(active_count)
        self.inactive_users_total.set(inactive_count)
        log.info(f"记录活跃用户统计: 活跃={active_count}, 不活跃={inactive_count}")
    
    def record_fetch_duration(self, username: str, duration: float):
        """记录抓取耗时"""
        self.fetch_duration.labels(username=username).observe(duration)
        log.debug(f"记录抓取耗时: {username} = {duration:.2f}s")
    
    def record_tweets_fetched(self, username: str, count: int):
        """记录抓取推文数"""
        self.tweets_fetched.labels(username=username).inc(count)
        log.info(f"记录推文抓取: {username} +{count}")
    
    def get_metrics_summary(self) -> Dict[str, any]:
        """获取指标摘要（用于日志输出）"""
        return {
            "prometheus_available": PROMETHEUS_AVAILABLE,
            "metrics_initialized": True
        }

# 全局指标实例
metrics = TwitterMetrics() 