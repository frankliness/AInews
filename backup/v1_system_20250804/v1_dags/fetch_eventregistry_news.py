"""
Airflow DAG – 每天 3 次抓取多源新闻 → Postgres raw_events
支持 Reuters、BBC、NYTimes、APNews、Bloomberg、TheGuardian、CNN、FT、SkyNews、ElPais、SCMP、AlJazeera、TheVerge 等13个源
"""
from __future__ import annotations
import os, sys, pathlib, logging
from datetime import datetime, timedelta

import pytz
import psycopg2
from airflow import DAG
from airflow.operators.python import PythonOperator

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))   # 让 Airflow 找到 scraper

from scraper import (
    ReutersScraper, BBCScraper, NYTimesScraper, APNewsScraper, 
    BloombergScraper, TheGuardianScraper, CNNScraper, FTScraper,
    SkyNewsScraper, ElPaisScraper, SCMPScraper, AlJazeeraScraper,
    TheVergeScraper
)  # noqa: E402

log = logging.getLogger(__name__)
SQL = """
INSERT INTO raw_events
(source,title,body,published_at,url,likes,retweets,event_id,embedding,total_articles_24h,source_importance,wgt,sentiment,collected_at)
VALUES (%(source)s,%(title)s,%(body)s,%(published_at)s,%(url)s,%(likes)s,%(retweets)s,%(event_id)s,%(embedding)s,%(total_articles_24h)s,%(source_importance)s,%(weight)s,%(sentiment)s,NOW())
ON CONFLICT (url) DO NOTHING;
"""

# Asia/Shanghai 时区
SH_TZ = pytz.timezone('Asia/Shanghai')

# 任务主体
def _fetch_eventregistry_news():
    """多源新闻抓取任务"""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError("缺少环境变量 DATABASE_URL")
    
    try:
        with psycopg2.connect(db_url) as conn:
            total = 0
            success_count = 0
            error_count = 0
            
            # 所有新闻源抓取器
            scrapers = [
                ReutersScraper, BBCScraper, NYTimesScraper, APNewsScraper,
                BloombergScraper, TheGuardianScraper, CNNScraper, FTScraper,
                SkyNewsScraper, ElPaisScraper, SCMPScraper, AlJazeeraScraper,
                TheVergeScraper
            ]
            
            for S in scrapers:
                try:
                    scraper = S()
                    log.info(f"开始抓取 {scraper.source}...")
                    
                    rows = list(scraper.run(conn))  # 传递数据库连接
                    
                    # 批量插入数据并统计实际插入数
                    inserted_count = 0
                    for it in rows:
                        try:
                            with conn.cursor() as cur:
                                cur.execute(SQL, it.as_dict())
                                if cur.rowcount > 0:  # 检查是否真的插入了
                                    inserted_count += 1
                        except Exception as e:
                            if "duplicate key value violates unique constraint" in str(e):
                                log.debug(f"跳过重复URL: {it.url}")
                                continue
                            else:
                                log.error(f"插入数据失败: {e}")
                                continue
                    
                    total += inserted_count
                    success_count += 1
                    log.info("✅ %s 抓取 %s 条，插入 %s 条", scraper.source, len(rows), inserted_count)
                    
                except Exception as e:
                    error_count += 1
                    log.error("❌ %s 抓取失败: %s", S.__name__, e)
                    
                    # 记录详细的错误信息
                    import traceback
                    log.error(f"详细错误信息: {traceback.format_exc()}")
                    
                    # 继续处理下一个抓取器，不中断整个任务
                    continue
            
            # 总结报告
            log.info("🎉 抓取完成总结:")
            log.info(f"  - 成功抓取: {success_count}/{len(scrapers)} 个源")
            log.info(f"  - 失败抓取: {error_count}/{len(scrapers)} 个源")
            log.info(f"  - 总插入行数: {total} 行")
            
            return f"inserted {total} rows from {success_count}/{len(scrapers)} sources"
    
    except psycopg2.Error as e:
        log.error(f"数据库连接失败: {e}")
        raise
    except Exception as e:
        log.error(f"任务执行失败: {e}")
        raise

# Airflow DAG 配置
# 注意：Airflow 默认 UTC，需换算北京时间
# 北京时间 10:00/17:00/22:00 = UTC 02:00/09:00/14:00
schedule_cron = "0 2,9,14 * * *"  # UTC时间，对应北京时间 10:00/17:00/22:00

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "depends_on_past": False,
    "email_on_failure": False,
}

with DAG(
    dag_id="fetch_eventregistry_news",
    description="多源新闻（Reuters、BBC、NYTimes等13个源）→ raw_events，每天 3 次（北京时间 10:00/17:00/22:00）",
    start_date=datetime(2025, 7, 1, tzinfo=pytz.UTC),
    schedule=schedule_cron,
    catchup=False,
    default_args=default_args,
    tags=["news", "eventregistry", "reuters", "bbc", "nytimes", "apnews", "bloomberg", "theguardian", "cnn", "ft", "skynews", "elpais", "scmp", "aljazeera", "theverge"],
) as dag:
    PythonOperator(
        task_id="fetch_eventregistry_news",
        python_callable=_fetch_eventregistry_news,
    ) 