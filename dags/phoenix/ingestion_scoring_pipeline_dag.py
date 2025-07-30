"""
Phoenix News Pipeline V2 - 精英数据动脉
集成信源过滤、数量控制和API消耗监控的新闻抓取流水线
"""

from datetime import datetime, timedelta
import logging
import json
import pandas as pd
import psycopg2
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable
from airflow.hooks.postgres_hook import PostgresHook
from airflow.exceptions import AirflowException
from eventregistry import EventRegistry, GetTrendingConcepts

# 导入我们的配置和客户端
from config.settings import MAX_EVENTS_TO_FETCH, ARTICLES_PER_EVENT
from scraper.newsapi_client import NewsApiClient
from db_utils import bulk_insert_articles
from advanced_scorer import AdvancedScorer

# 配置日志
log = logging.getLogger(__name__)

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

def fetch_data_with_monitoring():
    """
    一个集成了配置、监控和正确API调用的数据抓取任务。
    """
    # 从Airflow Variable获取API密钥
    api_key = Variable.get("EVENTREGISTRY_APIKEY")
    client = NewsApiClient(api_key=api_key)

    # --- 最终版：完全由Airflow Variable控制的信源过滤决策逻辑 ---
    import json
    # 1. 读取"是否启用白名单"的总开关
    # default_var='True' 意味着在变量不存在时，默认启用白名单，这是一个安全的设计
    try:
        enable_whitelist_str = Variable.get("ENABLE_SOURCE_WHITELIST", default_var='True')
        # 将字符串转换为布尔值
        should_use_whitelist = json.loads(enable_whitelist_str.lower())
    except Exception as e:
        log.error(f"Failed to parse ENABLE_SOURCE_WHITELIST. Defaulting to True. Error: {e}")
        should_use_whitelist = True
    
    trusted_sources_list = []
    # 2. 只有在"总开关"打开时，才去加载白名单列表
    if should_use_whitelist:
        try:
            trusted_sources_json = Variable.get("TRUSTED_SOURCES_WHITELIST", default_var='[]')
            trusted_sources_list = json.loads(trusted_sources_json)
            if not isinstance(trusted_sources_list, list):
                raise ValueError("Variable is not a valid JSON list.")
            log.info(f"✅ Successfully loaded {len(trusted_sources_list)} trusted sources from Variable.")
            # 如果白名单为空，则关闭开关，避免API报错
            if not trusted_sources_list:
                log.warning("Whitelist is enabled but the list is empty. Disabling whitelist for this run.")
                should_use_whitelist = False
        except (json.JSONDecodeError, ValueError) as e:
            log.error(f"Failed to parse TRUSTED_SOURCES_WHITELIST. Disabling whitelist. Error: {e}")
            should_use_whitelist = False
    
    log.info(f"Final decision on using whitelist: {should_use_whitelist}")
    # --- 决策逻辑结束 ---

    # 【核心修复】: 调用 eventregistry 客户端实例 (er) 的正确方法
    requests_before = client.er.getRemainingAvailableRequests()
    log.info(f"API requests remaining before run: {requests_before}")

    # 将最终的决策和白名单列表传递给客户端
    events = client.fetch_trending_events(
        source_names=trusted_sources_list,
        max_events=MAX_EVENTS_TO_FETCH,
        use_whitelist=should_use_whitelist # << 使用我们计算出的最终决策
    )

    all_articles = []
    # 2. 循环事件，使用配置文件中的文章数限制，获取文章
    for event in events:
        articles = client.fetch_rich_articles_for_event(
            event_uri=event['uri'],
            articles_count=ARTICLES_PER_EVENT
        )
        # 将事件级别的元数据（如总文章数）附加到每篇文章上，便于后续打分
        for article in articles:
            article['totalArticleCountInEvent'] = event.get('totalArticleCount', 0)
        all_articles.extend(articles)

    log.info(f"Total rich articles fetched: {len(all_articles)}")

    # --- 后续的批量写入数据库逻辑 ---
    if all_articles:
        # 调用我们新建的批量写入函数
        # 直接连接到Phoenix V2数据库
        bulk_insert_articles(
            articles=all_articles
        )
    else:
        log.info("本次运行没有抓取到任何新文章，无需写入数据库。")

    # 【核心修复】: 再次调用 eventregistry 客户端实例 (er) 的正确方法
    requests_after = client.er.getRemainingAvailableRequests()
    log.info(f"API requests remaining after run: {requests_after}")

    consumed = requests_before - requests_after
    log.info(f"✅ API requests consumed in this run: {consumed}")

def update_trending_concepts():
    """
    更新概念热度榜 - 流水线的第一个步骤
    
    生产版本：如果API调用失败，将抛出AirflowException，
    确保任务进入FAILED/UP_FOR_RETRY状态，方便告警与重试。
    """
    log.info("开始更新概念热度榜...")
    
    # 从Airflow Variable获取API密钥
    api_key = Variable.get("EVENTREGISTRY_APIKEY")
    er = EventRegistry(apiKey=api_key, allowUseOfArchive=False)
    
    try:
        # 调用GetTrendingConcepts API获取最新的概念热度榜
        query = GetTrendingConcepts(
            source="news",      # 我们只关心新闻中的热点
            count=200,          # 建议获取比100稍多的数量，以增加匹配概率
            conceptType=["person", "org", "loc"]  # 我们关心的三种实体类型
        )
        result = er.execQuery(query)
        
        # 处理API响应，构建概念热度字典
        # EventRegistry API返回的是列表格式
        if isinstance(result, list):
            items = result
        elif isinstance(result, dict):
            items = result.get("trendingConcepts") or result.get("results") or []
        else:
            raise ValueError("Unexpected API payload structure")
        
        if not items:
            raise ValueError("No trending concepts found in API response")
        
        concepts_to_insert = [
            (c["uri"],
             float(c["trendingScore"]["news"]["score"]),
             datetime.utcnow())
            for c in items
        ]
        
        log.info(f"API调用成功，获取到 {len(concepts_to_insert)} 个热门概念")
        
    except Exception as exc:
        # 记录错误并让Airflow处理失败/重试逻辑
        log.exception("❌ Failed to fetch trending concepts: %s", exc)
        raise AirflowException("Trending concept update failed") from exc
    
    # ------------------ UPSERT 到 Postgres ------------------
    db_config = {
        'host': 'postgres-phoenix',
        'port': 5432,
        'database': 'phoenix_db',
        'user': 'phoenix_user',
        'password': 'phoenix_pass',
        'options': '-c timezone=Asia/Shanghai'  # 设置连接时区
    }
    
    try:
        with psycopg2.connect(**db_config) as conn:
            with conn.cursor() as cur:
                from psycopg2.extras import execute_values
                execute_values(
                    cur,
                    """
                    INSERT INTO trending_concepts (uri, score, updated_at)
                    VALUES %s
                    ON CONFLICT (uri) DO UPDATE
                      SET score = EXCLUDED.score,
                          updated_at = EXCLUDED.updated_at;
                    """,
                    concepts_to_insert,
                    page_size=100,
                )
            conn.commit()
            log.info("✅ Upserted %d trending concepts", len(concepts_to_insert))
    except Exception as e:
        log.error(f"❌ 数据库UPSERT时发生错误: {e}")
        raise

def process_and_score_articles():
    """
    处理和评分文章 - 核心的"打分与更新"任务
    """
    log.info("开始处理和评分文章...")
    
    # 数据库连接配置
    db_config = {
        'host': 'postgres-phoenix',
        'port': 5432,
        'database': 'phoenix_db',
        'user': 'phoenix_user',
        'password': 'phoenix_pass'
    }
    
    try:
        with psycopg2.connect(**db_config) as conn:
            # 1. 加载外部大脑：从V2数据库的trending_concepts表中读取所有概念热度
            log.info("加载概念热度数据...")
            with conn.cursor() as cur:
                cur.execute("SELECT uri, score FROM trending_concepts")
                concepts_data = cur.fetchall()
                concepts_dict = {uri: score for uri, score in concepts_data}
                log.info(f"加载了 {len(concepts_dict)} 个概念的热度数据")
            
            # 2. 获取待处理数据：从raw_events表中查询所有final_score_v2 IS NULL的新文章
            log.info("查询待处理的新文章...")
            query_sql = """
            SELECT id, title, body, url, published_at, sentiment, source_name, 
                   source_importance, event_uri, total_articles_in_event, concepts
            FROM raw_events 
            WHERE final_score_v2 IS NULL
            ORDER BY collected_at DESC
            """
            
            articles_df = pd.read_sql_query(query_sql, conn)
            log.info(f"找到 {len(articles_df)} 篇待处理文章")
            
            if articles_df.empty:
                log.info("没有需要处理的新文章，任务完成")
                return
            
            # 处理concepts列 - 将JSON字符串转换为Python对象
            articles_df['concepts'] = articles_df['concepts'].apply(
                lambda x: json.loads(x) if x and isinstance(x, str) else x
            )
            
            # 3. 调用智慧核心：实例化AdvancedScorer并进行打分
            log.info("初始化AdvancedScorer并开始打分...")
            scorer = AdvancedScorer(concepts_dict)
            scored_df = scorer.score(articles_df)
            
            # 4. 结果写回数据库：更新raw_events表中对应的行
            log.info("将打分结果写回数据库...")
            with conn.cursor() as cur:
                update_sql = """
                UPDATE raw_events SET
                    entity_hot_score = %s,
                    hot_score_v2 = %s,
                    rep_score_v2 = %s,
                    sent_score_v2 = %s,
                    hot_norm = %s,
                    rep_norm = %s,
                    sent_norm = %s,
                    final_score_v2 = %s
                WHERE id = %s
                """
                
                update_data = []
                for _, row in scored_df.iterrows():
                    update_data.append((
                        float(row['entity_hot_score']),
                        float(row['hot_score_v2']),
                        float(row['rep_score_v2']),
                        float(row['sent_score_v2']),
                        float(row['hot_norm']),
                        float(row['rep_norm']),
                        float(row['sent_norm']),
                        float(row['final_score_v2']),
                        row['id']
                    ))
                
                cur.executemany(update_sql, update_data)
                conn.commit()
                
                log.info(f"✅ 成功更新 {len(update_data)} 篇文章的分数")
                
                # 输出一些统计信息
                avg_score = scored_df['final_score_v2'].mean()
                max_score = scored_df['final_score_v2'].max()
                log.info(f"📊 打分统计 - 平均分: {avg_score:.4f}, 最高分: {max_score:.4f}")
    
    except Exception as e:
        log.error(f"❌ 处理和评分文章时发生错误: {e}")
        raise



# 创建DAG
dag = DAG(
    'ingestion_scoring_pipeline',
    default_args=default_args,
    description='高频运行的新闻抓取与高级打分流水线',
    schedule_interval='0 2,9,14 * * *',  # 北京时间10:00, 17:00, 22:00 (UTC 2:00, 9:00, 14:00)
    catchup=False,
    tags=['phoenix', 'ingestion', 'scoring'],
)

# 定义任务
update_trending_concepts_task = PythonOperator(
    task_id='update_trending_concepts',
    python_callable=update_trending_concepts,
    dag=dag,
)

fetch_task = PythonOperator(
    task_id='fetch_data_with_monitoring',
    python_callable=fetch_data_with_monitoring,
    dag=dag,
)

process_task = PythonOperator(
    task_id='process_and_score_articles',
    python_callable=process_and_score_articles,
    dag=dag,
)

# 设置任务依赖
update_trending_concepts_task >> fetch_task >> process_task 