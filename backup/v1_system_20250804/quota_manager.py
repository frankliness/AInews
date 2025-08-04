"""
配额管理模块
实现动态配额分配、窗口管理和安全余量控制
"""
import time
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from .config import config

log = logging.getLogger(__name__)

@dataclass
class QuotaInfo:
    """配额信息"""
    remaining: int
    reset_time: Optional[int] = None
    limit: Optional[int] = None
    window_start: Optional[datetime] = None

@dataclass
class UserQuota:
    """用户配额分配"""
    username: str
    user_id: str
    allocated_quota: int
    used_quota: int = 0
    is_completed: bool = False

class QuotaManager:
    """配额管理器"""
    
    def __init__(self):
        self.current_quota = QuotaInfo(remaining=0)
        self.user_quotas: Dict[str, UserQuota] = {}
        self.window_start = None
    
    def update_quota_info(self, remaining: int, reset_time: Optional[int] = None, limit: Optional[int] = None):
        """更新配额信息"""
        self.current_quota.remaining = remaining
        self.current_quota.reset_time = reset_time
        self.current_quota.limit = limit
        
        if not self.window_start:
            self.window_start = datetime.now(ZoneInfo("Asia/Shanghai"))
            self.current_quota.window_start = self.window_start
    
    def calculate_available_budget(self) -> int:
        """计算可用预算"""
        # 预留安全余量
        available = max(0, self.current_quota.remaining - config.safety_margin)
        log.info(f"配额信息: remaining={self.current_quota.remaining}, safety_margin={config.safety_margin}, available={available}")
        return available
    
    def allocate_quotas(self, active_users: List[Tuple[str, str]]) -> Dict[str, UserQuota]:
        """为活跃用户分配配额"""
        available_budget = self.calculate_available_budget()
        
        if available_budget <= 0:
            log.warning("可用预算不足，等待窗口重置")
            return {}
        
        N = len(active_users)
        if N == 0:
            log.info("无活跃用户，跳过配额分配")
            return {}
        
        # 基础配额分配
        base_quota = available_budget // N
        remainder = available_budget % N
        
        log.info(f"配额分配: 总预算={available_budget}, 用户数={N}, 基础配额={base_quota}, 余数={remainder}")
        
        # 分配配额给每个用户
        self.user_quotas = {}
        for i, (username, user_id) in enumerate(active_users):
            # 基础配额
            allocated = base_quota
            
            # 余数按顺序分配给前几个用户
            if i < remainder:
                allocated += 1
            
            self.user_quotas[username] = UserQuota(
                username=username,
                user_id=user_id,
                allocated_quota=allocated
            )
            
            log.info(f"用户 {username} 分配配额: {allocated}")
        
        return self.user_quotas
    
    def check_quota_available(self, username: str) -> bool:
        """检查用户是否还有可用配额"""
        if username not in self.user_quotas:
            return False
        
        user_quota = self.user_quotas[username]
        return user_quota.used_quota < user_quota.allocated_quota and not user_quota.is_completed
    
    def consume_quota(self, username: str, amount: int = 1):
        """消耗用户配额"""
        if username in self.user_quotas:
            self.user_quotas[username].used_quota += amount
            log.debug(f"用户 {username} 消耗配额: {amount}, 已用: {self.user_quotas[username].used_quota}/{self.user_quotas[username].allocated_quota}")
    
    def mark_user_completed(self, username: str):
        """标记用户完成"""
        if username in self.user_quotas:
            self.user_quotas[username].is_completed = True
            log.info(f"用户 {username} 配额使用完成")
    
    def get_quota_utilization(self) -> float:
        """获取配额利用率"""
        if not self.user_quotas:
            return 0.0
        
        total_allocated = sum(q.allocated_quota for q in self.user_quotas.values())
        total_used = sum(q.used_quota for q in self.user_quotas.values())
        
        if total_allocated == 0:
            return 0.0
        
        utilization = (total_used / total_allocated) * 100
        log.info(f"配额利用率: {utilization:.1f}% ({total_used}/{total_allocated})")
        return utilization
    
    def should_wait_for_reset(self) -> bool:
        """检查是否需要等待窗口重置"""
        if self.current_quota.remaining <= config.safety_margin:
            if self.current_quota.reset_time:
                now = datetime.now(ZoneInfo("Asia/Shanghai")).timestamp()
                wait_time = max(0, self.current_quota.reset_time - now + 1)
                if wait_time > 0:
                    log.warning(f"配额耗尽，等待 {wait_time:.1f} 秒后重置")
                    time.sleep(wait_time)
                    return True
            else:
                log.warning("配额耗尽但无重置时间，等待60秒")
                time.sleep(60)
                return True
        
        return False
    
    def get_active_users_with_quota(self) -> List[Tuple[str, str]]:
        """获取还有配额的用户列表"""
        return [
            (username, user_quota.user_id)
            for username, user_quota in self.user_quotas.items()
            if self.check_quota_available(username)
        ]
    
    def log_quota_summary(self):
        """记录配额使用摘要"""
        if not self.user_quotas:
            return
        
        log.info("=== 配额使用摘要 ===")
        for username, user_quota in self.user_quotas.items():
            status = "完成" if user_quota.is_completed else "进行中"
            log.info(f"用户 {username}: {user_quota.used_quota}/{user_quota.allocated_quota} ({status})")
        
        utilization = self.get_quota_utilization()
        log.info(f"总体利用率: {utilization:.1f}%")
        log.info("==================") 