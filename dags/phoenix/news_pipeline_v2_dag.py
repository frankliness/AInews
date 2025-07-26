"""
Phoenix V2 新闻流水线 DAG
使用事件优先策略的新一代新闻分析系统
"""
from datetime import datetime, timedelta
import logging
import sys
import os
from typing import List, Dict, Any

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.models import Variable

# 添加项目根目录到路径
sys.path.append('/opt/airflow')

from scraper.newsapi_client import NewsAPIClient

# 配置日志
log = logging.getLogger(__name__)

# DAG配置
default_args = {
    'owner': 'phoenix',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'phoenix_news_pipeline',
    default_args=default_args,
    description='Phoenix V2 事件优先新闻流水线',
    schedule_interval='0 * * * *',  # 每小时执行一次
    catchup=False,
    tags=['phoenix', 'v2', 'news'],
)

def fetch_and_ingest_news(**context):
    """
    获取并入库新闻数据的主函数
    """
    log.info("🚀 Phoenix V2 开始执行新闻抓取任务")
    
    try:
        # a. 从Airflow Variable中获取 NEWSAPI_AI_KEY
        api_key = Variable.get("NEWSAPI_AI_KEY")
        log.info("✅ 成功获取API密钥")
        
        # b. 实例化 NewsAPIClient
        client = NewsAPIClient(api_key)
        
        # c. 调用 fetch_trending_events_uris，获取热门事件URI
        category_uris = [
            "dmoz/Business",
            "dmoz/Technology", 
            "dmoz/Politics",
            "dmoz/Health",
            "dmoz/Science"
        ]
        date_start = datetime.now() - timedelta(hours=24)
        
        event_uris = client.fetch_trending_events_uris(category_uris, date_start)
        
        if not event_uris:
            log.warning("⚠️ 未获取到任何事件URI")
            return
        
        # 测试阶段：只处理前5个事件
        event_uris = event_uris[:5]
        log.info(f"📊 获取到 {len(event_uris)} 个事件URI (测试模式，仅处理前5个)")
        
        # d. 创建空列表 all_articles
        all_articles = []
        
        # e. 循环遍历URI，获取文章数据
        for event_uri in event_uris:
            articles = client.fetch_rich_articles_for_event(event_uri)
            all_articles.extend(articles)
            
            # 添加小延迟避免API限制
            import time
            time.sleep(0.5)
        
        log.info(f"📰 总共获取到 {len(all_articles)} 篇文章")
        
        if not all_articles:
            log.warning("⚠️ 未获取到任何文章数据")
            return
        
        # f. 使用PostgresHook批量插入数据
        pg_hook = PostgresHook(postgres_conn_id='postgres_phoenix_shadow')
        
        # 准备插入数据
        insert_data = []
        for article in all_articles:
            row = (
                article.get("title", ""),
                article.get("body", ""),
                article.get("url", ""),
                article.get("published_at"),
                article.get("sentiment", 0.0),
                article.get("relevance", 1.0),
                article.get("weight", 1.0),
                article.get("event_uri", ""),
                article.get("source_name", ""),
                article.get("source_importance", 1),
                article.get("total_articles_24h", 0),
                article.get("embedding"),
                datetime.now(),  # collected_at
                "phoenix_v2"  # source
            )
            insert_data.append(row)
        
        # 执行批量插入
        columns = [
            "title", "body", "url", "published_at", "sentiment", 
            "relevance", "weight", "event_uri", "source_name", 
            "source_importance", "total_articles_24h", "embedding",
            "collected_at", "source"
        ]
        
        pg_hook.insert_rows(
            table="raw_events",
            rows=insert_data,
            target_fields=columns
        )
        
        log.info(f"✅ 成功插入 {len(insert_data)} 条记录到 phoenix_shadow.raw_events")
        
        # 设置任务成功状态
        context['task_instance'].xcom_push(key='articles_count', value=len(all_articles))
        context['task_instance'].xcom_push(key='events_count', value=len(event_uris))
        
    except Exception as e:
        log.error(f"❌ Phoenix V2 任务执行失败: {e}")
        raise

# 创建任务
fetch_and_ingest_task = PythonOperator(
    task_id='fetch_and_ingest_task',
    python_callable=fetch_and_ingest_news,
    provide_context=True,
    dag=dag,
)

# 任务依赖关系（目前只有一个任务）
fetch_and_ingest_task 