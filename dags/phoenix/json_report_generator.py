# 文件路径: pipeline/json_report_generator.py
import logging
from datetime import datetime, timezone
import json
import pandas as pd
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# 引入统一的时间工具模块
from dags.phoenix.time_utils import (
    get_cutoff_hour, logical_date_bj, prev_logical_date_str, utc_to_bj
)

log = logging.getLogger(__name__)

def generate_summary_report_to_json_file(**context):
    """
    生成每日新闻摘要JSON报告
    严格遵循"北京时间6AM"规则进行新闻筛选
    """
    log.info("📊 开始生成每日新闻摘要JSON报告...")
    
    # 获取可配置的cutoff小时数
    try:
        from airflow.models import Variable
        cutoff_hour = get_cutoff_hour(lambda k: Variable.get(k, default_var=None))
    except Exception:
        cutoff_hour = get_cutoff_hour()
    
    log.debug(f"使用北京时间日界cutoff={cutoff_hour}小时")
    
    # 从Airflow上下文获取DAG的逻辑运行日期
    logical_date = context['ds']
    log.info(f"为逻辑日期 {logical_date} 生成报告...")
    
    # 直接使用psycopg2连接Phoenix V2数据库
    db_config = {
        'host': 'postgres-phoenix',
        'port': 5432,
        'database': 'phoenix_db',
        'user': 'phoenix_user',
        'password': 'phoenix_pass',
        'options': '-c timezone=Asia/Shanghai'  # 设置连接时区
    }
    
    # 1. 【核心修复】: 实现"北京时间6AM"规则的SQL查询 + 事件去重
    # 逻辑: 数据库中的published_at已经是北京时间，直接减去cutoff_hour小时，
    # 然后取其日期部分与DAG的逻辑运行日期进行比较。
    # 新增: 使用CTE和窗口函数，确保每个event_uri最多2篇文章
    sql = f"""
    WITH ranked_articles AS (
        SELECT
            final_score_v2, title, body, source_name, url, event_uri, published_at,
            ROW_NUMBER() OVER(
                PARTITION BY event_uri 
                ORDER BY final_score_v2 DESC
            ) as rn
        FROM public.raw_events
        WHERE
            final_score_v2 IS NOT NULL
            AND (published_at - INTERVAL '{cutoff_hour} hours')::date = '{logical_date}'::date
    )
    SELECT
        final_score_v2, title, body, source_name, url, event_uri, published_at
    FROM ranked_articles
    WHERE rn <= 2
    ORDER BY final_score_v2 DESC;
    """
    
    log.info(f"📰 正在从数据库中读取Top 100已打分的新闻（应用北京时间{cutoff_hour}AM日界规则）...")
    
    try:
        with psycopg2.connect(**db_config) as conn:
            df = pd.read_sql_query(sql, conn)
    except Exception as e:
        log.error(f"❌ 数据库查询失败: {e}")
        raise
    
    if df.empty:
        log.warning(f"在 {logical_date} 的时间范围内未找到任何已打分的新闻，无法生成报告。")
        return
    
    log.info(f"✅ 成功读取 {len(df)} 篇文章用于生成摘要。")
    
    # 添加debug日志，显示时间处理详情
    if df['published_at'].notna().any():
        sample_published_at = df['published_at'].dropna().iloc[0]
        sample_bj = utc_to_bj(sample_published_at)
        sample_logical_date = logical_date_bj(sample_published_at, cutoff_hour)
        log.debug(
            "时间处理示例 - cutoff=%s, published_at=%s, bj_time=%s, logical_date=%s",
            cutoff_hour, 
            sample_published_at.isoformat(), 
            sample_bj.isoformat(), 
            sample_logical_date
        )
    
    # 2. 构建符合"契约"的JSON对象
    now_utc = datetime.now(timezone.utc)
    report_data = {
        "reportMetadata": {
            "reportGeneratedAt": now_utc.isoformat(),
            "reportForDate": logical_date,
            "articleCount": len(df),
            "dataSource": "Phoenix V2 Pipeline"
        },
        "articles": []
    }
    
    for index, row in df.iterrows():
        article_object = {
            "rank": index + 1,
            "score": round(row['final_score_v2'], 4) if pd.notna(row['final_score_v2']) else None,
            "source": row['source_name'],
            "title": row['title'],
            "url": row['url'],
            "publishedAt": row['published_at'].isoformat() if pd.notna(row['published_at']) else None,
            "eventId": row['event_uri'],
            "body": row['body']
        }
        report_data["articles"].append(article_object)
    
    # 3. 将JSON对象写入带时间戳的文件
    output_dir = "/opt/airflow/exports"
    # 文件名包含逻辑日期和执行时间，区分调度和手动运行
    run_type = "scheduled" if context.get('dag_run').run_id.startswith('scheduled') else "manual"
    filename = f"summary_{logical_date}_{run_type}_{now_utc.strftime('%H-%M-%S')}.json"
    output_path = os.path.join(output_dir, filename)
    
    log.info(f"💾 正在将JSON报告写入到文件: {output_path}")
    
    try:
        os.makedirs(output_dir, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        log.info(f"✅ JSON报告生成成功！文件: {filename}")
    except Exception as e:
        log.error(f"❌ 写入JSON报告文件时发生错误: {e}")
        raise 