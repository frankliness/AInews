"""
用户活跃度分析模块
实现活跃度评估、过滤和统计功能
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

from .config import config

log = logging.getLogger(__name__)

@dataclass
class UserActivity:
    """用户活跃度信息"""
    username: str
    user_id: str
    last_tweet_at: Optional[datetime] = None
    tweets_24h: int = 0
    tweets_7d: int = 0
    is_active: bool = False
    skip_reason: Optional[str] = None
    inactive_rounds: int = 0

class ActivityAnalyzer:
    """活跃度分析器"""
    
    def __init__(self):
        self.log_dir = Path("logs/news/twitter")
        self.activity_file = self.log_dir / "user_activity.json"
        self.inactive_counts_file = self.log_dir / "inactive_counts.json"
    
    def load_activity_data(self) -> Dict[str, UserActivity]:
        """加载用户活跃度数据"""
        activity_data = {}
        
        # 从日志文件分析活跃度
        if self.log_dir.exists():
            for log_file in self.log_dir.glob("twitter_*.log"):
                activity_data.update(self._analyze_log_file(log_file))
        
        # 加载历史不活跃计数
        inactive_counts = self._load_inactive_counts()
        
        # 合并数据
        for username, activity in activity_data.items():
            activity.inactive_rounds = inactive_counts.get(username, 0)
        
        return activity_data
    
    def _analyze_log_file(self, log_file: Path) -> Dict[str, UserActivity]:
        """分析日志文件中的用户活跃度"""
        activity_data = {}
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    try:
                        data = json.loads(line)
                        
                        # 跳过限速事件
                        if data.get("event_type") == "rate_limit":
                            continue
                        
                        username = data.get("username", "")
                        if not username:
                            continue
                        
                        # 解析时间
                        published_at = datetime.fromisoformat(data["published_at"].replace("Z", "+00:00"))
                        
                        # 更新用户活跃度
                        if username not in activity_data:
                            activity_data[username] = UserActivity(
                                username=username,
                                user_id=data.get("user_id", ""),
                                last_tweet_at=published_at,
                                tweets_24h=0,
                                tweets_7d=0
                            )
                        else:
                            # 更新最新推文时间
                            if published_at > activity_data[username].last_tweet_at:
                                activity_data[username].last_tweet_at = published_at
                        
                        # 统计24小时和7天内的推文数
                        now = datetime.now(ZoneInfo("Asia/Shanghai"))
                        if published_at > now - timedelta(hours=24):
                            activity_data[username].tweets_24h += 1
                        if published_at > now - timedelta(days=7):
                            activity_data[username].tweets_7d += 1
                            
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
                        
        except Exception as e:
            log.warning(f"分析日志文件 {log_file} 失败: {e}")
        
        return activity_data
    
    def _load_inactive_counts(self) -> Dict[str, int]:
        """加载历史不活跃计数"""
        try:
            if self.inactive_counts_file.exists():
                with open(self.inactive_counts_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            log.warning(f"加载不活跃计数失败: {e}")
        
        return {}
    
    def _save_inactive_counts(self, inactive_counts: Dict[str, int]):
        """保存不活跃计数"""
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            with open(self.inactive_counts_file, 'w', encoding='utf-8') as f:
                json.dump(inactive_counts, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log.error(f"保存不活跃计数失败: {e}")
    
    def evaluate_activity(self, users: List[str]) -> Tuple[List[str], List[UserActivity]]:
        """评估用户活跃度，返回活跃用户列表和所有用户活跃度信息"""
        activity_data = self.load_activity_data()
        now = datetime.now(ZoneInfo("Asia/Shanghai"))
        
        active_users = []
        all_activities = []
        inactive_counts = self._load_inactive_counts()
        
        for username in users:
            activity = activity_data.get(username, UserActivity(
                username=username,
                user_id="",
                last_tweet_at=None,
                tweets_24h=0,
                tweets_7d=0
            ))
            
            # 评估活跃度
            is_active = self._check_activity_criteria(activity, now)
            activity.is_active = is_active
            
            if is_active:
                active_users.append(username)
                # 重置不活跃计数
                inactive_counts[username] = 0
            else:
                # 增加不活跃计数
                inactive_counts[username] = inactive_counts.get(username, 0) + 1
                activity.inactive_rounds = inactive_counts[username]
                activity.skip_reason = self._get_skip_reason(activity, now)
            
            all_activities.append(activity)
        
        # 保存不活跃计数
        self._save_inactive_counts(inactive_counts)
        
        # 记录跳过信息
        self._log_skipped_users(all_activities)
        
        log.info(f"活跃度评估完成: {len(active_users)}/{len(users)} 用户活跃")
        return active_users, all_activities
    
    def _check_activity_criteria(self, activity: UserActivity, now: datetime) -> bool:
        """检查活跃度标准"""
        # 标准1: 最近推文时间在活跃窗口内
        if activity.last_tweet_at:
            days_since_last = (now - activity.last_tweet_at).days
            if days_since_last <= config.active_window_days:
                return True
        
        # 标准2: 24小时内推文数达到阈值
        if activity.tweets_24h >= config.min_tweets_24h:
            return True
        
        # 标准3: 7天内推文数达到阈值
        if activity.tweets_7d >= config.min_tweets_7d:
            return True
        
        return False
    
    def _get_skip_reason(self, activity: UserActivity, now: datetime) -> str:
        """获取跳过原因"""
        reasons = []
        
        if not activity.last_tweet_at:
            reasons.append("无历史推文")
        else:
            days_since_last = (now - activity.last_tweet_at).days
            if days_since_last > config.active_window_days:
                reasons.append(f"最后推文{days_since_last}天前")
        
        if activity.tweets_24h < config.min_tweets_24h:
            reasons.append(f"24h内推文{activity.tweets_24h}条(需{config.min_tweets_24h}条)")
        
        if activity.tweets_7d < config.min_tweets_7d:
            reasons.append(f"7天内推文{activity.tweets_7d}条(需{config.min_tweets_7d}条)")
        
        return "; ".join(reasons)
    
    def _log_skipped_users(self, activities: List[UserActivity]):
        """记录被跳过的用户"""
        skipped_users = [a for a in activities if not a.is_active]
        
        if skipped_users:
            try:
                # 写入系统日志文件，而不是推文日志文件
                log_dir = Path("logs/system")
                log_dir.mkdir(parents=True, exist_ok=True)
                
                now = datetime.now(ZoneInfo("Asia/Shanghai"))
                log_file = log_dir / f"twitter_activity_{now.strftime('%Y-%m-%d')}.log"
                
                for activity in skipped_users:
                    skip_data = {
                        "timestamp": now.isoformat(),
                        "event_type": "user_skipped",
                        "username": activity.username,
                        "user_id": activity.user_id,
                        "reason": activity.skip_reason,
                        "last_tweet_at": activity.last_tweet_at.isoformat() if activity.last_tweet_at else None,
                        "tweets_24h": activity.tweets_24h,
                        "tweets_7d": activity.tweets_7d,
                        "inactive_rounds": activity.inactive_rounds
                    }
                    
                    with open(log_file, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(skip_data, ensure_ascii=False) + '\n')
                        
            except Exception as e:
                log.error(f"记录跳过用户失败: {e}")
            
            # 检查是否需要告警
            for activity in skipped_users:
                if activity.inactive_rounds >= config.inactive_skip_rounds:
                    log.warning(f"用户 {activity.username} 连续 {activity.inactive_rounds} 轮不活跃，建议移出抓取列表") 