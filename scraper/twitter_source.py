"""
Twitter v2 抓取器 - 无阻塞版本
实现配额平均分配、活跃度过滤、用户ID缓存、精确分页和全链路可观测
- 无阻塞：窗口配额用完即结束，不等待重置
- 高效缓存：持久化用户ID，避免重复API调用
- 精确分页：分页次数 = 切片配额，无二次削减
- 全链路可观测：Prometheus指标覆盖分配→消耗→耗尽
"""
from __future__ import annotations
import os
import time
import logging
import requests
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Iterable, Dict, Optional, List, Tuple
from dataclasses import dataclass

from .base import ScrapedItem, BaseScraper
from .utils import is_within_24h, log_tweet_record_with_aggregation, check_duplicate_tweet_id
from .config import config
from .activity_analyzer import ActivityAnalyzer
from .quota_manager import QuotaManager
from .user_cache import UserCacheManager
from .metrics import metrics
from .exceptions import WindowExhausted, TwitterRateLimitError, UserNotFoundError

log = logging.getLogger(__name__)

_BEARER = os.getenv("TWITTER_BEARER_TOKEN") or os.getenv("TW_BEARER_TOKEN")
_USERS = [u.strip() for u in os.getenv("TWITTER_USERS", "").split(",") if u.strip()]
_API = "https://api.twitter.com/2"

def _headers():
    return {"Authorization": f"Bearer {_BEARER}"}

def _parse_rate_limit_headers(response: requests.Response) -> Tuple[int, Optional[int], Optional[int]]:
    """解析限速头信息"""
    remaining = int(response.headers.get('x-rate-limit-remaining', 0))
    reset_time = int(response.headers.get('x-rate-limit-reset', 0)) if response.headers.get('x-rate-limit-reset') else None
    limit = int(response.headers.get('x-rate-limit-limit', 0)) if response.headers.get('x-rate-limit-limit') else None
    
    return remaining, reset_time, limit

def _check_window_exhausted(remaining: int, safety_margin: int) -> bool:
    """检查窗口是否耗尽"""
    return remaining <= safety_margin

def _fetch_user_id_from_api(username: str, quota_manager: QuotaManager) -> Optional[int]:
    """从API获取用户ID"""
    try:
        r = requests.get(f"{_API}/users/by/username/{username}", headers=_headers())
        
        # 解析限速信息
        remaining, reset_time, limit = _parse_rate_limit_headers(r)
        quota_manager.update_quota_info(remaining, reset_time, limit)
        
        # 消耗配额
        quota_manager.consume_quota(username, 1)
        
        # 检查窗口耗尽
        if _check_window_exhausted(remaining, config.safety_margin):
            log.warning(f"获取用户ID时窗口耗尽: {username}, remaining={remaining}")
            raise WindowExhausted(reset_time, f"获取用户ID时窗口耗尽: {username}")
        
        # 检查限速
        if r.status_code == 429 or r.status_code == 403:
            metrics.record_rate_limit("users_by_username")
            log.warning(f"获取用户ID时收到限速: {username}, status={r.status_code}")
            raise TwitterRateLimitError(f"Rate limited for user {username}")
        
        r.raise_for_status()
        user_data = r.json()["data"]
        
        log.info(f"成功获取用户ID: {username} -> {user_data['id']}")
        return int(user_data["id"])
        
    except (WindowExhausted, TwitterRateLimitError):
        raise
    except Exception as e:
        log.error(f"获取用户ID失败 {username}: {e}")
        return None

def _fetch_tweets_with_quota(user_id: int, username: str, quota_manager: QuotaManager, 
                           user_cache: UserCacheManager) -> List[dict]:
    """根据配额限制获取用户推文"""
    tweets = []
    start_time = time.time()
    
    try:
        # 获取用户配额
        user_quota = quota_manager.user_quotas.get(username)
        if not user_quota:
            log.warning(f"用户 {username} 无配额分配")
            return []
        
        # 计算允许的页数
        allowed_pages = min(config.max_pages_per_user, user_quota.allocated_quota)
        log.info(f"用户 {username} 配额: {user_quota.allocated_quota}, 允许页数: {allowed_pages}")
        
        # 记录配额分配指标
        metrics.record_quota_assigned(username, allowed_pages)
        
        params = {
            "max_results": config.max_results_per_request,
            "tweet.fields": "created_at,public_metrics",
            "exclude": "retweets,replies",
        }
        
        # 添加 since_id 参数（如果存在）
        user_progress = _load_user_progress()
        if username in user_progress and user_progress[username].get("since_id"):
            params["since_id"] = user_progress[username]["since_id"]
        
        next_token = None
        page_count = 0
        
        while page_count < allowed_pages and quota_manager.check_quota_available(username):
            if next_token:
                params["pagination_token"] = next_token
            
            r = requests.get(f"{_API}/users/{user_id}/tweets", params=params, headers=_headers())
            
            # 更新配额信息
            remaining, reset_time, limit = _parse_rate_limit_headers(r)
            quota_manager.update_quota_info(remaining, reset_time, limit)
            
            # 消耗配额
            quota_manager.consume_quota(username, 1)
            metrics.record_quota_used(username, 1)
            
            # 检查窗口耗尽
            if _check_window_exhausted(remaining, config.safety_margin):
                log.warning(f"用户 {username} 抓取时窗口耗尽: remaining={remaining}")
                raise WindowExhausted(reset_time, f"抓取用户 {username} 时窗口耗尽")
            
            # 检查限速
            if r.status_code == 429 or r.status_code == 403:
                metrics.record_rate_limit("users_tweets")
                log.warning(f"用户 {username} 触发限速: status={r.status_code}, remaining={remaining}")
                raise TwitterRateLimitError(f"Rate limited for user {username}")
            
            r.raise_for_status()
            data = r.json()
            
            page_tweets = data.get("data", [])
            if not page_tweets:
                break
            
            # 为每条推文添加用户名和用户ID
            for tweet in page_tweets:
                tweet["username"] = username
                tweet["user_id"] = str(user_id)
            
            tweets.extend(page_tweets)
            
            # 更新最新推文ID
            if page_tweets:
                _update_user_progress(username, page_tweets[0]["id"])
            
            # 检查是否有下一页
            next_token = data.get("meta", {}).get("next_token")
            if not next_token:
                break
            
            page_count += 1
        
        # 标记用户完成
        quota_manager.mark_user_completed(username)
        
        # 记录性能指标
        duration = time.time() - start_time
        metrics.record_fetch_duration(username, duration)
        metrics.record_tweets_fetched(username, len(tweets))
        
        log.info(f"用户 {username} 抓取完成: {len(tweets)}条推文, {page_count}页, 耗时{duration:.2f}s")
        return tweets
        
    except (WindowExhausted, TwitterRateLimitError):
        raise
    except Exception as e:
        log.error(f"获取用户推文失败 {username}: {e}")
        return []

def _load_user_progress() -> Dict[str, dict]:
    """加载用户进度"""
    progress_file = "logs/news/twitter/user_progress.json"
    try:
        if os.path.exists(progress_file):
            with open(progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        log.warning(f"加载用户进度失败: {e}")
    
    return {}

def _update_user_progress(username: str, last_tweet_id: str):
    """更新用户进度"""
    progress_file = "logs/news/twitter/user_progress.json"
    try:
        progress = _load_user_progress()
        if username not in progress:
            progress[username] = {}
        
        progress[username]["since_id"] = last_tweet_id
        progress[username]["last_updated"] = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
        
        os.makedirs(os.path.dirname(progress_file), exist_ok=True)
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        log.error(f"更新用户进度失败: {e}")

def _log_window_exhausted_event(reset_timestamp: Optional[int], reason: str):
    """记录窗口耗尽事件"""
    try:
        # 写入系统日志文件，而不是推文日志文件
        log_dir = Path("logs/system")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        now = datetime.now(ZoneInfo("Asia/Shanghai"))
        log_file = log_dir / f"twitter_quota_{now.strftime('%Y-%m-%d')}.log"
        
        event_data = {
            "timestamp": now.isoformat(),
            "event_type": "window_exhausted",
            "reason": reason,
            "reset_timestamp": reset_timestamp,
            "remaining_calls": 0
        }
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event_data, ensure_ascii=False) + '\n')
            
    except Exception as e:
        log.error(f"记录窗口耗尽事件失败: {e}")

class TwitterScraper(BaseScraper):
    source = "twitter"

    def __init__(self, db_connection=None):
        super().__init__()
        self.db_connection = db_connection
        self.activity_analyzer = ActivityAnalyzer()
        self.quota_manager = QuotaManager()
        self.user_cache = UserCacheManager(db_connection, config.user_id_cache_table)

    def fetch(self):
        if not _BEARER or not _USERS:
            log.warning("TWITTER env 未配置，直接返回空")
            return iter([])
        
        log.info(f"开始Twitter抓取，配置用户数: {len(_USERS)}")
        
        try:
            # 1. 活跃度评估
            active_users, all_activities = self.activity_analyzer.evaluate_activity(_USERS)
            
            # 记录活跃度指标
            metrics.record_active_users(len(active_users), len(_USERS) - len(active_users))
            
            if not active_users:
                log.warning("无活跃用户，跳过抓取")
                return iter([])
            
            log.info(f"活跃用户: {', '.join(active_users)}")
            
            # 2. 批量获取用户ID（优先从缓存）
            user_ids = self.user_cache.batch_get_user_ids(active_users)
            missing_users = self.user_cache.get_missing_users(active_users)
            
            # 记录缓存指标
            if user_ids:
                metrics.record_cache_hit()
            if missing_users:
                metrics.record_cache_miss()
            
            # 3. 为缺失用户获取ID
            for username in missing_users:
                try:
                    user_id = _fetch_user_id_from_api(username, self.quota_manager)
                    if user_id:
                        self.user_cache.set_user_id(username, user_id)
                        user_ids[username] = user_id
                    else:
                        log.warning(f"跳过用户 {username}：无法获取用户ID")
                except WindowExhausted as e:
                    log.warning(f"获取用户ID时窗口耗尽: {e}")
                    _log_window_exhausted_event(e.reset_timestamp, str(e))
                    metrics.record_window_exhausted()
                    return iter([])
                except TwitterRateLimitError:
                    log.warning(f"跳过用户 {username}：API限速")
                    continue
                except Exception as e:
                    log.error(f"处理用户 {username} 时出错: {e}")
                    continue
            
            if not user_ids:
                log.warning("无有效用户ID，跳过抓取")
                return iter([])
            
            # 4. 配额分配
            active_users_with_ids = [(username, user_id) for username, user_id in user_ids.items()]
            user_quotas = self.quota_manager.allocate_quotas(active_users_with_ids)
            
            if not user_quotas:
                log.warning("配额分配失败，跳过抓取")
                return iter([])
            
            # 5. 按配额拉取推文
            all_tweets = []
            skipped_users = []
            
            for username, user_id in active_users_with_ids:
                if not self.quota_manager.check_quota_available(username):
                    log.info(f"用户 {username} 配额已用完，跳过")
                    continue
                
                try:
                    tweets = _fetch_tweets_with_quota(user_id, username, self.quota_manager, self.user_cache)
                    all_tweets.extend(tweets)
                    
                except WindowExhausted as e:
                    # 记录窗口耗尽事件
                    _log_window_exhausted_event(e.reset_timestamp, str(e))
                    metrics.record_window_exhausted()
                    log.warning(f"抓取过程中窗口耗尽: {e}")
                    break  # 立即结束本轮抓取
                    
                except TwitterRateLimitError:
                    # 记录限速事件
                    metrics.record_rate_limit("users_tweets")
                    skipped_users.append(username)
                    log.warning(f"用户 {username} 因限速跳过，继续下一个用户")
                    continue
                except Exception as e:
                    log.error(f"处理用户 {username} 时出错: {e}")
                    skipped_users.append(username)
                    continue
            
            # 6. 记录统计信息
            if skipped_users:
                log.info(f"本轮抓取跳过用户: {', '.join(skipped_users)}")
            
            # 7. 配额使用摘要
            self.quota_manager.log_quota_summary()
            
            log.info(f"本轮抓取完成: {len(all_tweets)}条推文, {len(active_users_with_ids)}个活跃用户")
            return iter(all_tweets)
            
        except Exception as e:
            log.error(f"Twitter抓取过程中出现错误: {e}")
            return iter([])

    def parse(self, raw: Iterable[dict], db_connection=None):
        collected_at = datetime.now(ZoneInfo("Asia/Shanghai"))
        
        for tw in raw:
            # 解析发布时间
            published_at = datetime.fromisoformat(tw["created_at"].replace("Z","+00:00")).astimezone(timezone.utc)
            
            # 时间过滤：只处理过去24小时内的数据
            if not is_within_24h(published_at):
                log.debug(f"跳过过期推文: {tw['text'][:50]}...")
                continue
            
            # 获取推文信息
            tweet_id = tw["id"]
            text = tw["text"]
            metrics_data = tw.get("public_metrics", {})
            
            # 去重检查
            if db_connection:
                if check_duplicate_tweet_id(tweet_id, db_connection):
                    log.debug(f"跳过重复推文ID: {tweet_id}")
                    continue
            
            # 记录到日志文件并触发汇总
            try:
                log_tweet_record_with_aggregation(
                    source=self.source,
                    collected_at=collected_at,
                    published_at=published_at,
                    username=tw.get("username", ""),
                    user_id=tw.get("user_id", ""),
                    text=text,
                    retweet_count=metrics_data.get("retweet_count", 0),
                    reply_count=metrics_data.get("reply_count", 0),
                    like_count=metrics_data.get("like_count", 0),
                    quote_count=metrics_data.get("quote_count", 0),
                    impression_count=metrics_data.get("impression_count", 0)
                )
            except Exception as e:
                log.error(f"记录推文日志失败: {e}")
            
            yield ScrapedItem(
                source       = self.source,
                title        = "",
                body         = text,
                published_at = published_at,
                url          = f"https://twitter.com/i/web/status/{tweet_id}",
                likes        = metrics_data.get("like_count", 0),
                retweets     = metrics_data.get("retweet_count", 0),
            )
