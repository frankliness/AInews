"""
Airflow DAG – 手动触发，分析每日新闻 sentiment 分布（直接从原始新闻源日志读取）
"""
from __future__ import annotations
import os, sys, pathlib, logging, json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List
import numpy as np

from airflow import DAG
from airflow.operators.python import PythonOperator

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

log = logging.getLogger(__name__)

# 所有新闻源目录（可根据实际情况补充/调整）
NEWS_SOURCES = [
    "reuters", "bbc", "apnews", "bloomberg", "nytimes", "theguardian",
    "cnn", "ft", "elpais", "scmp", "skynews", "aljazeera", "theverge"
]

LOGS_BASE = Path("logs/news")


def analyze_sentiment_for_date(target_date: str, **context):
    """
    遍历所有新闻源目录，读取指定日期的日志文件，统计 sentiment 分布
    :param target_date: 日期字符串 YYYY-MM-DD
    """
    date_obj = datetime.strptime(target_date, "%Y-%m-%d")
    all_sentiments = []
    total_records = 0
    source_stats = {}

    for source in NEWS_SOURCES:
        source_dir = LOGS_BASE / source
        if not source_dir.exists():
            continue
        # 支持多种命名格式，如 reuters_2025-07-11.log 或 2025-07-11.log
        log_files = list(source_dir.glob(f"*{target_date}*.log")) + list(source_dir.glob(f"*{target_date}*.json"))
        source_sentiments = []
        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                            s = record.get('sentiment')
                            if isinstance(s, (int, float)):
                                all_sentiments.append(s)
                                source_sentiments.append(s)
                        except Exception:
                            continue
            except Exception as e:
                log.warning(f"读取文件失败: {log_file} - {e}")
        if source_sentiments:
            source_stats[source] = len(source_sentiments)
            total_records += len(source_sentiments)

    if not all_sentiments:
        log.warning(f"未找到任何 sentiment 数据，日期: {target_date}")
        print(f"❌ 未找到任何 sentiment 数据，日期: {target_date}")
        return

    arr = np.array(all_sentiments)
    print(f"【{target_date}】共提取 {len(arr)} 条新闻的 sentiment")
    print(f"均值: {arr.mean():.4f}")
    print(f"中位数: {np.median(arr):.4f}")
    print(f"最大值: {arr.max():.4f}")
    print(f"最小值: {arr.min():.4f}")
    print(f"标准差: {arr.std():.4f}")
    print(f"来源分布: {source_stats}")
    # 分布区间统计
    bins = [-1, -0.8, -0.6, -0.4, -0.2, 0, 0.2, 0.4, 0.6, 0.8, 1]
    hist, edges = np.histogram(arr, bins=bins)
    print("\n分布区间统计：")
    for i in range(len(hist)):
        print(f"{edges[i]:>5.1f} ~ {edges[i+1]:>4.1f} : {hist[i]:3d} 条")
    # 可选：写入本地文件
    out_path = Path(f"exports/sentiment_stats_{target_date}.txt")
    with open(out_path, 'w', encoding='utf-8') as fw:
        fw.write(f"【{target_date}】共提取 {len(arr)} 条新闻的 sentiment\n")
        fw.write(f"均值: {arr.mean():.4f}\n")
        fw.write(f"中位数: {np.median(arr):.4f}\n")
        fw.write(f"最大值: {arr.max():.4f}\n")
        fw.write(f"最小值: {arr.min():.4f}\n")
        fw.write(f"标准差: {arr.std():.4f}\n")
        fw.write(f"来源分布: {source_stats}\n")
        fw.write("\n分布区间统计：\n")
        for i in range(len(hist)):
            fw.write(f"{edges[i]:>5.1f} ~ {edges[i+1]:>4.1f} : {hist[i]:3d} 条\n")
    print(f"\n统计结果已写入: {out_path}")

# DAG定义
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
}

dag = DAG(
    'analyze_daily_sentiment',
    default_args=default_args,
    description='分析每日新闻 sentiment 分布（原始日志）',
    schedule='@daily',  # 每天运行一次
    catchup=False,
    tags=['analysis', 'sentiment', 'news'],
)

analyze_task = PythonOperator(
    task_id='analyze_daily_sentiment',
    python_callable=analyze_sentiment_for_date,
    op_kwargs={'target_date': '{{ dag_run.conf["date"] if dag_run and dag_run.conf and "date" in dag_run.conf else ds }}'},
    dag=dag,
) 