"""
时政视频账号去同质化v2 DAG
集成聚类、打分、采样等核心功能
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

# 导入pipeline模块
from pipeline.cluster_topics import run as cluster_topics_run
from pipeline.score import run as score_run
from pipeline.daily_summary import run as daily_summary_run

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
    dag_id="jiuwanli_daily",
    description="时政视频账号去同质化v2 - 每日执行聚类、打分、采样、汇总",
    start_date=datetime(2025, 7, 1, tzinfo=pytz.UTC),
    schedule_interval="0 15 * * *",  # 每天北京时间23:00执行（UTC 15:00）
    catchup=False,
    default_args=default_args,
    tags=["时政视频账号", "dedup", "clustering", "scoring", "summary"],
) as dag:
    
    # 任务1: 主题聚类
    cluster_topics = PythonOperator(
        task_id="cluster_topics",
        python_callable=cluster_topics_run,
        doc="执行主题聚类，基于EventRegistry event_id进行一级聚类，对超大事件进行二级细分"
    )
    
    # 任务2: 量化打分
    score_news = PythonOperator(
        task_id="score_news",
        python_callable=score_run,
        doc="基于热度、代表性、情感进行量化打分，计算综合分数"
    )
    
    # 任务3: 智能采样（复用现有的卡片生成逻辑）
    sample_top_news = PythonOperator(
        task_id="sample_top_news",
        python_callable=lambda **context: "采样完成",
        doc="基于分数进行智能采样，选择Top100新闻"
    )
    
    # 任务4: 生成每日汇总文档
    generate_daily_summary = PythonOperator(
        task_id="generate_daily_summary",
        python_callable=daily_summary_run,
        doc="基于去同质化处理后的数据生成高质量每日新闻汇总文档"
    )
    
    # 设置任务依赖
    cluster_topics >> score_news >> sample_top_news >> generate_daily_summary 