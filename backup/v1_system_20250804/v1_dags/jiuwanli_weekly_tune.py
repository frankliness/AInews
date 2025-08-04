"""
时政视频账号周度自动调参DAG
每周一执行参数自动优化
"""
from __future__ import annotations

# 立即设置Python路径，确保在导入任何模块之前就配置好
import sys
if '/opt/airflow' not in sys.path:
    sys.path.insert(0, '/opt/airflow')

import pathlib, logging
from datetime import datetime, timedelta

import pytz
from airflow import DAG
from airflow.operators.python import PythonOperator

# 修复路径配置，确保在Docker容器中能正确找到模块
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# 导入自动调参模块
from pipeline.auto_tune import run as auto_tune_run

log = logging.getLogger(__name__)

# 默认参数
default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "depends_on_past": False,
    "email_on_failure": False,
}

# 创建DAG
with DAG(
    dag_id="jiuwanli_weekly_tune",
    description="时政视频账号周度自动调参 - 每周一执行参数优化",
    start_date=datetime(2025, 7, 1, tzinfo=pytz.UTC),
    schedule_interval="0 3 * * MON",  # 每周一凌晨3点执行
    catchup=False,
    default_args=default_args,
    tags=["时政视频账号", "auto_tune", "parameter_optimization"],
) as dag:
    
    # 自动调参任务
    auto_tune = PythonOperator(
        task_id="auto_tune",
        python_callable=auto_tune_run,
        doc="基于过去7天历史数据，使用逻辑回归模型自动优化热度系数和混合权重"
    ) 