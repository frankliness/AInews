"""
Twitter 抓取异常类
"""
from typing import Optional

class WindowExhausted(Exception):
    """窗口配额耗尽异常"""
    
    def __init__(self, reset_timestamp: Optional[int] = None, message: str = "API窗口配额耗尽"):
        self.reset_timestamp = reset_timestamp
        self.message = message
        super().__init__(self.message)
    
    def __str__(self):
        if self.reset_timestamp:
            return f"{self.message} (重置时间: {self.reset_timestamp})"
        return self.message

class TwitterRateLimitError(Exception):
    """Twitter API 限速异常"""
    pass

class UserNotFoundError(Exception):
    """用户未找到异常"""
    pass 