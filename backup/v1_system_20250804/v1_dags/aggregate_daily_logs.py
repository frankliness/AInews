"""
Airflow DAG – 每天凌晨12点汇总前一天的新闻日志
按照规则：当天凌晨6点前采集的新闻汇总时放在前一天
所有时间以北京时间为准
"""
from __future__ import annotations
import os, sys, pathlib, logging
from datetime import datetime, timedelta

import pytz
from airflow import DAG
from airflow.operators.python import PythonOperator

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))   # 让 Airflow 找到 scraper

from scraper.log_aggregator import LogAggregator

log = logging.getLogger(__name__)

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def _aggregate_daily_logs():
    """
    汇总前一天的新闻日志
    
    规则：
    - 每天凌晨12点执行
    - 汇总前一天的日志（以北京时间为准）
    - 当天凌晨6点前采集的新闻汇总时放在前一天
    """
    # 获取当前北京时间
    now_beijing = datetime.now(BEIJING_TZ)
    
    # 计算目标日期
    # 如果当前时间在凌晨0-6点之间，汇总前一天的日志
    # 如果当前时间在凌晨6点之后，汇总当天的日志
    if now_beijing.hour < 6:
        # 凌晨0-6点，汇总前一天的日志
        target_date = (now_beijing - timedelta(days=1)).date()
        log.info(f"当前北京时间: {now_beijing.strftime('%Y-%m-%d %H:%M:%S')}")
        log.info(f"汇总前一天 ({target_date}) 的日志")
    else:
        # 凌晨6点之后，汇总当天的日志
        target_date = now_beijing.date()
        log.info(f"当前北京时间: {now_beijing.strftime('%Y-%m-%d %H:%M:%S')}")
        log.info(f"汇总当天 ({target_date}) 的日志")
    
    try:
        # 创建汇总器
        aggregator = LogAggregator("logs/news")
        
        # 执行汇总
        result = aggregator.aggregate_daily_logs(target_date)
        
        if result:
            log.info(f"✅ 日志汇总成功:")
            log.info(f"  - 汇总文件: {result['log']}")
            log.info(f"  - JSON文件: {result['json']}")
            return f"汇总完成: {target_date}"
        else:
            log.warning(f"⚠️ 未找到 {target_date} 的日志文件")
            return f"未找到日志: {target_date}"
            
    except Exception as e:
        log.error(f"❌ 日志汇总失败: {e}")
        import traceback
        log.error(f"详细错误信息: {traceback.format_exc()}")
        raise

# Airflow DAG 配置
# 每天凌晨12点执行（北京时间）
schedule_cron = "0 0 * * *"  # 每天00:00执行

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "depends_on_past": False,
    "email_on_failure": False,
}

with DAG(
    dag_id="aggregate_daily_logs",
    description="每天凌晨12点汇总前一天的新闻日志（北京时间）",
    start_date=datetime(2025, 7, 1, tzinfo=pytz.UTC),
    schedule=schedule_cron,
    catchup=False,
    default_args=default_args,
    tags=["logs", "aggregation", "daily"],
) as dag:
    PythonOperator(
        task_id="aggregate_daily_logs",
        python_callable=_aggregate_daily_logs,
    ) 