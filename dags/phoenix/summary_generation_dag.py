"""
Phoenix Summary Generation DAG - 每日新闻摘要JSON报告生成器
严格遵循"北京时间6AM"规则的数据消费流水线
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from json_report_generator import generate_summary_report_to_json_file

# DAG 默认参数
default_args = {
    'owner': 'phoenix',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# 创建DAG
dag = DAG(
    'summary_generation_dag',
    default_args=default_args,
    description='生成每日Top 100新闻摘要JSON报告 (按6AM规则)',
    schedule_interval='0 15 * * *',  # 北京时间23:00 (UTC 15:00)
    catchup=False,
    tags=['phoenix', 'summary', 'report'],
)

# 定义任务 - 连接JSON报告生成器
generate_summary_report_task = PythonOperator(
    task_id='generate_summary_report_task',
    python_callable=generate_summary_report_to_json_file,
    dag=dag,
) 