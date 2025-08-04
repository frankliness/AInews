# 文件路径: dags/phoenix/db_utils.py
import logging
import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone
import pytz

log = logging.getLogger(__name__)

def convert_to_beijing_time(utc_time_str):
    """
    将UTC时间字符串转换为北京时间
    """
    if not utc_time_str:
        return None
    
    try:
        # 解析UTC时间字符串
        if isinstance(utc_time_str, str):
            # 处理不同的时间格式
            if utc_time_str.endswith('Z'):
                utc_dt = datetime.fromisoformat(utc_time_str[:-1]).replace(tzinfo=timezone.utc)
            elif '+' in utc_time_str or utc_time_str.endswith('+00:00'):
                utc_dt = datetime.fromisoformat(utc_time_str)
                if utc_dt.tzinfo is None:
                    utc_dt = utc_dt.replace(tzinfo=timezone.utc)
            else:
                utc_dt = datetime.fromisoformat(utc_time_str).replace(tzinfo=timezone.utc)
        else:
            utc_dt = utc_time_str
            
        # 转换为北京时间
        beijing_tz = pytz.timezone('Asia/Shanghai')
        beijing_dt = utc_dt.astimezone(beijing_tz)
        
        log.debug(f"时间转换: {utc_time_str} -> {beijing_dt.isoformat()}")
        return beijing_dt
    except Exception as e:
        log.warning(f"时间转换失败: {utc_time_str}, 错误: {e}")
        return None

def get_current_beijing_time():
    """
    获取当前北京时间
    """
    beijing_tz = pytz.timezone('Asia/Shanghai')
    return datetime.now(beijing_tz)

def bulk_insert_articles(articles: list, conn_id: str = None):
    """
    将一个文章字典列表批量插入到raw_events表中。
    这个函数会自动处理JSON序列化、时间转换(UTC->北京时间)和ON CONFLICT逻辑。
    """
    if not articles:
        log.info("文章列表为空，无需执行数据库写入。")
        return

    log.info(f"准备将 {len(articles)} 篇文章批量写入数据库...")
    
    # 直接使用环境变量连接Phoenix V2数据库
    db_config = {
        'host': 'postgres-phoenix',
        'port': 5432,
        'database': 'phoenix_db',
        'user': 'phoenix_user',
        'password': 'phoenix_pass',
        'options': '-c timezone=Asia/Shanghai'  # 设置连接时区
    }

    # 准备要插入的数据元组列表
    # 我们需要将Python字典转换为数据库表对应的字段顺序
    insert_tuples = []
    current_beijing_time = get_current_beijing_time()
    log.info(f"当前北京时间: {current_beijing_time.isoformat()}")
    
    for article in articles:
        # 将concepts列表安全地转换为JSON字符串
        concepts_json = json.dumps(article.get('concepts')) if article.get('concepts') else None
        
        # 将UTC时间转换为北京时间
        published_at_beijing = convert_to_beijing_time(article.get('dateTimePub'))
        if published_at_beijing:
            log.debug(f"文章发布时间转换: {article.get('dateTimePub')} -> {published_at_beijing.isoformat()}")
        else:
            log.warning(f"无法转换发布时间: {article.get('dateTimePub')}")
            published_at_beijing = current_beijing_time
        
        # 解析 importanceRank
        importance_rank = None  # 默认值
        if 'source' in article and article.get('source') and 'ranking' in article['source'] and article['source'].get('ranking'):
            importance_rank = article['source']['ranking'].get('importanceRank')
        
        insert_tuples.append(
            (
                article.get('uri'),
                article.get('title'),
                article.get('body'),
                article.get('url'),
                published_at_beijing,  # 转换为北京时间
                current_beijing_time,  # collected_at 使用当前北京时间
                article.get('sentiment'),
                article.get('source', {}).get('uri'),
                importance_rank,  # 使用解析到的 importanceRank
                article.get('eventUri'),
                # 附加的事件级元数据
                article.get('totalArticleCountInEvent', 0),
                # 将concepts的JSON字符串加入
                concepts_json
            )
        )
    
    # 定义目标表的字段，确保顺序与上面的元组完全对应
    target_fields = [
        'id', 'title', 'body', 'url', 'published_at', 'collected_at', 'sentiment',
        'source_name', 'source_importance', 'event_uri', 
        'total_articles_in_event', 'concepts'
    ]
    
    # 使用psycopg2直接连接数据库并执行批量插入
    try:
        with psycopg2.connect(**db_config) as conn:
            with conn.cursor() as cur:
                # 构建批量插入SQL语句，使用ON CONFLICT DO NOTHING
                insert_sql = """
                INSERT INTO raw_events (
                    id, title, body, url, published_at, collected_at, sentiment,
                    source_name, source_importance, event_uri, 
                    total_articles_in_event, concepts
                ) VALUES %s
                ON CONFLICT (id) DO NOTHING
                """
                
                # 使用psycopg2的execute_values进行高效批量插入
                from psycopg2.extras import execute_values
                execute_values(cur, insert_sql, insert_tuples, template=None, page_size=100)
                
                conn.commit()
                log.info(f"✅ 成功将 {len(insert_tuples)} 篇文章写入数据库。")
    except Exception as e:
        log.error(f"❌ 批量写入数据库时发生错误: {e}")
        raise 