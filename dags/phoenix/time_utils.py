"""
Phoenix 时间工具模块

提供统一的北京时间6AM日界处理逻辑，用于Phoenix新闻摘要生成系统。
所有时间计算基于Asia/Shanghai时区，支持可配置的日界cutoff时间。

核心概念：
- 逻辑日期：北京时间0:00-(cutoff-1):59计入前一日，否则为当日
- 默认cutoff=6，即北京时间6AM作为日界
"""

from __future__ import annotations
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
import os
import logging
from typing import Optional, Callable

# 常量定义
BJ_TZ = ZoneInfo("Asia/Shanghai")
UTC_TZ = ZoneInfo("UTC")

logger = logging.getLogger(__name__)


def get_cutoff_hour(get_var_fn: Optional[Callable[[str], str]] = None) -> int:
    """
    返回北京时间日界小时（默认6）。
    
    优先级顺序：
    1) get_var_fn("bj_cutoff_hour") 若传入且成功
    2) 环境变量 BJ_CUTOFF_HOUR
    3) 默认值 6
    
    Args:
        get_var_fn: 可传入Airflow Variable读函数，如 lambda k: Variable.get(k, default_var=None)
        
    Returns:
        int: 日界小时数 (0-23)
        
    Examples:
        >>> get_cutoff_hour()  # 默认返回6
        6
        
        >>> import os
        >>> os.environ['BJ_CUTOFF_HOUR'] = '8'
        >>> get_cutoff_hour()  # 返回8
        8
    """
    val = None
    
    # 尝试从Airflow Variable获取
    if get_var_fn:
        try:
            val = get_var_fn("bj_cutoff_hour")
        except Exception:
            val = None
    
    # 尝试从环境变量获取
    if val is None:
        val = os.getenv("BJ_CUTOFF_HOUR")
    
    # 解析并验证
    try:
        cutoff = int(val) if val is not None else 6
    except ValueError:
        cutoff = 6
    
    # 确保在有效范围内
    if not (0 <= cutoff <= 23):
        cutoff = 6
        
    return cutoff


def utc_to_bj(dt_utc: datetime) -> datetime:
    """
    将UTC时间（aware或naive）转换为北京时间（aware）。
    
    如果传入naive datetime，视为UTC时间进行转换。
    
    Args:
        dt_utc: UTC时间，可以是aware或naive
        
    Returns:
        datetime: 北京时间（aware）
        
    Examples:
        >>> from datetime import datetime
        >>> from zoneinfo import ZoneInfo
        >>> utc_dt = datetime(2025, 9, 1, 16, 5, tzinfo=ZoneInfo("UTC"))
        >>> bj_dt = utc_to_bj(utc_dt)
        >>> bj_dt.hour
        0
        >>> bj_dt.day
        2
    """
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=UTC_TZ)
    return dt_utc.astimezone(BJ_TZ)


def logical_date_bj(dt_utc: datetime, cutoff_hour: int = 6) -> date:
    """
    基于北京时间与cutoff，返回"逻辑日期"。
    
    规则：北京时间0:00-(cutoff-1):59计入前一日，否则为当日。
    
    Args:
        dt_utc: UTC时间
        cutoff_hour: 日界小时数，默认6
        
    Returns:
        date: 逻辑日期
        
    Examples:
        >>> from datetime import datetime
        >>> from zoneinfo import ZoneInfo
        >>> # UTC 2025-09-01 16:05:00 -> BJ 2025-09-02 00:05 -> 返回 2025-09-01
        >>> dt1 = datetime(2025, 9, 1, 16, 5, tzinfo=ZoneInfo("UTC"))
        >>> logical_date_bj(dt1, 6)
        datetime.date(2025, 9, 1)
        
        >>> # UTC 2025-09-01 22:00:00 -> BJ 2025-09-02 06:00 -> 返回 2025-09-02
        >>> dt2 = datetime(2025, 9, 1, 22, 0, tzinfo=ZoneInfo("UTC"))
        >>> logical_date_bj(dt2, 6)
        datetime.date(2025, 9, 2)
    """
    bj = utc_to_bj(dt_utc)
    if bj.hour < cutoff_hour:
        bj = bj - timedelta(days=1)
    return bj.date()


def prev_logical_date_str(run_dt_utc: datetime, cutoff_hour: int = 6) -> str:
    """
    给Airflow run_dt（UTC），返回"前一日（北京口径）"的YYYY-MM-DD字符串。
    
    语义：每日早06:00（BJT）运行 -> 对应昨天的逻辑日期（等价于BJ当日减一日的日历日）。
    
    Args:
        run_dt_utc: Airflow运行时间（UTC）
        cutoff_hour: 日界小时数，默认6
        
    Returns:
        str: 前一日逻辑日期的YYYY-MM-DD格式字符串
        
    Examples:
        >>> from datetime import datetime
        >>> from zoneinfo import ZoneInfo
        >>> # 运行时间：UTC 2025-09-02 00:30 -> BJ 2025-09-02 08:30 -> 前一日为 2025-09-01
        >>> run_dt = datetime(2025, 9, 2, 0, 30, tzinfo=ZoneInfo("UTC"))
        >>> prev_logical_date_str(run_dt, 6)
        '2025-09-01'
    """
    bj_now = utc_to_bj(run_dt_utc)
    y_bj = bj_now - timedelta(days=1)
    return y_bj.strftime("%Y-%m-%d")


def now_prev_logical_date_str(cutoff_hour: int = 6) -> str:
    """
    便捷函数，直接返回"当下时间"的前一日逻辑日期字符串。
    
    用于临时工具/脚本，便于快速获取前一日日期。
    
    Args:
        cutoff_hour: 日界小时数，默认6
        
    Returns:
        str: 前一日逻辑日期的YYYY-MM-DD格式字符串
        
    Examples:
        >>> # 假设当前UTC时间为2025-09-02 01:00:00
        >>> now_prev_logical_date_str(6)  # 返回 '2025-09-01'
        '2025-09-01'
    """
    return prev_logical_date_str(datetime.now(tz=UTC_TZ), cutoff_hour)
