"""
Twitter 用户ID缓存管理器
实现用户ID的持久化缓存，避免重复调用API
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, List, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor

from .exceptions import UserNotFoundError

log = logging.getLogger(__name__)

class UserCacheManager:
    """用户ID缓存管理器"""
    
    def __init__(self, db_connection=None, cache_table: str = "twitter_users"):
        self.db_connection = db_connection
        self.cache_table = cache_table
        self._cache: Dict[str, int] = {}  # 内存缓存
    
    def get_user_id(self, username: str) -> Optional[int]:
        """获取用户ID（优先从缓存）"""
        # 先查内存缓存
        if username in self._cache:
            log.debug(f"从内存缓存获取用户ID: {username} -> {self._cache[username]}")
            return self._cache[username]
        
        # 查数据库缓存
        if self.db_connection:
            try:
                with self.db_connection.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        f"SELECT id FROM {self.cache_table} WHERE username = %s",
                        (username,)
                    )
                    result = cursor.fetchone()
                    
                    if result:
                        user_id = result['id']
                        self._cache[username] = user_id
                        log.debug(f"从数据库缓存获取用户ID: {username} -> {user_id}")
                        return user_id
                        
            except Exception as e:
                log.warning(f"查询用户ID缓存失败 {username}: {e}")
        
        return None
    
    def set_user_id(self, username: str, user_id: int) -> bool:
        """设置用户ID缓存"""
        try:
            # 更新内存缓存
            self._cache[username] = user_id
            
            # 更新数据库缓存
            if self.db_connection:
                with self.db_connection.cursor() as cursor:
                    cursor.execute(
                        f"""
                        INSERT INTO {self.cache_table} (id, username, updated_at)
                        VALUES (%s, %s, NOW())
                        ON CONFLICT (username) 
                        DO UPDATE SET 
                            id = EXCLUDED.id,
                            updated_at = NOW()
                        """,
                        (user_id, username)
                    )
                    self.db_connection.commit()
                    
                log.info(f"缓存用户ID: {username} -> {user_id}")
                return True
                
        except Exception as e:
            log.error(f"缓存用户ID失败 {username}: {e}")
            return False
    
    def get_missing_users(self, usernames: List[str]) -> List[str]:
        """获取缓存中缺失的用户列表"""
        missing = []
        
        for username in usernames:
            if not self.get_user_id(username):
                missing.append(username)
        
        log.info(f"缓存缺失用户: {missing}")
        return missing
    
    def batch_get_user_ids(self, usernames: List[str]) -> Dict[str, int]:
        """批量获取用户ID（优先从缓存）"""
        user_ids = {}
        
        for username in usernames:
            user_id = self.get_user_id(username)
            if user_id:
                user_ids[username] = user_id
        
        log.info(f"批量获取用户ID: {len(user_ids)}/{len(usernames)} 命中缓存")
        return user_ids
    
    def clear_cache(self, username: Optional[str] = None):
        """清除缓存"""
        if username:
            self._cache.pop(username, None)
            log.info(f"清除用户缓存: {username}")
        else:
            self._cache.clear()
            log.info("清除所有内存缓存")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """获取缓存统计信息"""
        return {
            "memory_cache_size": len(self._cache),
            "total_users": len(self._cache)
        } 