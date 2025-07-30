#!/usr/bin/env python3
"""
Phoenix 数据库时间转换脚本
将 raw_events 表中的 UTC 时间转换为北京时间
"""

import psycopg2
import logging
from datetime import datetime, timezone
import pytz

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

def convert_phoenix_timestamps():
    """
    转换 Phoenix 数据库中的时间戳从 UTC 到北京时间
    """
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
            with conn.cursor() as cur:
                log.info("开始转换 Phoenix 数据库中的时间戳...")
                
                # 1. 检查当前数据状态
                cur.execute("SELECT COUNT(*) FROM raw_events")
                total_count = cur.fetchone()[0]
                log.info(f"数据库中共有 {total_count} 条记录")
                
                # 2. 更新 published_at 字段 (从 UTC 转为北京时间)
                update_published_sql = """
                UPDATE raw_events 
                SET published_at = published_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Shanghai'
                WHERE published_at IS NOT NULL
                  AND published_at::text NOT LIKE '%+08:00%'
                  AND published_at::text NOT LIKE '%+08%'
                """
                
                cur.execute(update_published_sql)
                published_updated = cur.rowcount
                log.info(f"✅ 更新了 {published_updated} 条记录的 published_at 字段")
                
                # 3. 更新 collected_at 字段 (从 UTC 转为北京时间)
                update_collected_sql = """
                UPDATE raw_events 
                SET collected_at = collected_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Shanghai'
                WHERE collected_at IS NOT NULL
                  AND collected_at::text NOT LIKE '%+08:00%'
                  AND collected_at::text NOT LIKE '%+08%'
                """
                
                cur.execute(update_collected_sql)
                collected_updated = cur.rowcount
                log.info(f"✅ 更新了 {collected_updated} 条记录的 collected_at 字段")
                
                # 4. 对于没有 collected_at 的记录，设置为当前北京时间
                current_beijing_time = datetime.now(pytz.timezone('Asia/Shanghai'))
                set_collected_sql = """
                UPDATE raw_events 
                SET collected_at = %s
                WHERE collected_at IS NULL
                """
                
                cur.execute(set_collected_sql, (current_beijing_time,))
                collected_set = cur.rowcount
                log.info(f"✅ 为 {collected_set} 条记录设置了 collected_at 字段")
                
                # 5. 验证转换结果
                cur.execute("SELECT COUNT(*) FROM raw_events WHERE published_at IS NOT NULL")
                total_count = cur.fetchone()[0]
                
                cur.execute("""
                    SELECT COUNT(*) FROM raw_events 
                    WHERE published_at IS NOT NULL 
                    AND published_at::text LIKE '%+08%'
                """)
                beijing_count = cur.fetchone()[0]
                
                log.info(f"📊 验证结果: 总计 {total_count} 条记录，其中 {beijing_count} 条为北京时间格式")
                
                # 6. 显示转换后的示例数据
                cur.execute("""
                    SELECT published_at, collected_at 
                    FROM raw_events 
                    ORDER BY collected_at DESC 
                    LIMIT 3
                """)
                sample_data = cur.fetchall()
                log.info("📋 转换后的示例数据:")
                for i, (published_at, collected_at) in enumerate(sample_data, 1):
                    log.info(f"  记录 {i}: published_at={published_at}, collected_at={collected_at}")
                
                # 提交事务
                conn.commit()
                log.info("🎉 Phoenix 数据库时间转换完成！")
                
    except Exception as e:
        log.error(f"❌ 转换 Phoenix 数据库时发生错误: {e}")
        raise

if __name__ == "__main__":
    convert_phoenix_timestamps() 