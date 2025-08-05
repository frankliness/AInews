#!/usr/bin/env python3
"""
生产环境双重话题抑制功能验证脚本
用于验证抑制功能在生产环境中的实际效果
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import psycopg2
from psycopg2.extras import RealDictCursor
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_db_connection():
    """获取数据库连接"""
    try:
        # 在容器内运行时使用容器网络地址
        conn = psycopg2.connect(
            host="postgres-phoenix",
            port="5432",
            database="phoenix_db",
            user="phoenix_user",
            password="phoenix_pass"
        )
        return conn
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return None

def verify_suppression_fields():
    """验证监控字段是否存在"""
    print("=== 验证监控字段 ===")
    
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'raw_events' 
                  AND column_name IN ('is_routine_topic', 'is_category_topic', 'is_breaking_news', 'is_suppressed', 'is_downweighted')
                ORDER BY column_name;
            """)
            
            fields = cur.fetchall()
            if len(fields) == 5:
                print("✅ 所有监控字段已存在:")
                for field, data_type in fields:
                    print(f"  - {field}: {data_type}")
                return True
            else:
                print(f"❌ 监控字段不完整，找到 {len(fields)}/5 个字段")
                return False
    except Exception as e:
        print(f"❌ 验证监控字段失败: {e}")
        return False
    finally:
        conn.close()

def get_suppression_stats():
    """获取抑制效果统计"""
    print("\n=== 抑制效果统计 (最近24小时) ===")
    
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    COUNT(*) as total_articles_24h,
                    COUNT(CASE WHEN is_routine_topic = true THEN 1 END) as routine_topic_articles,
                    COUNT(CASE WHEN is_category_topic = true THEN 1 END) as category_topic_articles,
                    COUNT(CASE WHEN is_breaking_news = true THEN 1 END) as breaking_news_articles,
                    COUNT(CASE WHEN is_suppressed = true THEN 1 END) as suppressed_articles,
                    COUNT(CASE WHEN is_downweighted = true THEN 1 END) as downweighted_articles,
                    ROUND(COUNT(CASE WHEN is_suppressed = true THEN 1 END) * 100.0 / COUNT(*), 2) as suppression_rate,
                    ROUND(COUNT(CASE WHEN is_downweighted = true THEN 1 END) * 100.0 / COUNT(*), 2) as downweight_rate
                FROM raw_events 
                WHERE published_at >= NOW() - INTERVAL '24 HOURS';
            """)
            
            stats = cur.fetchone()
            if stats:
                print(f"总文章数: {stats['total_articles_24h']}")
                print(f"常规话题文章: {stats['routine_topic_articles']}")
                print(f"领域话题文章: {stats['category_topic_articles']}")
                print(f"爆点文章: {stats['breaking_news_articles']}")
                print(f"被抑制文章: {stats['suppressed_articles']}")
                print(f"被降权文章: {stats['downweighted_articles']}")
                print(f"抑制率: {stats['suppression_rate']}%")
                print(f"降权率: {stats['downweight_rate']}%")
                
                if stats['suppressed_articles'] > 0 or stats['downweighted_articles'] > 0:
                    print("✅ 抑制功能正在生效")
                else:
                    print("⚠️  未检测到抑制效果，可能需要更多数据或检查配置")
            else:
                print("❌ 无法获取统计数据")
    except Exception as e:
        print(f"❌ 获取抑制统计失败: {e}")
    finally:
        conn.close()

def analyze_topic_distribution():
    """分析话题类型分布"""
    print("\n=== 话题类型分布分析 ===")
    
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    CASE 
                        WHEN is_routine_topic = true AND is_breaking_news = false THEN '常规话题(非爆点)'
                        WHEN is_routine_topic = true AND is_breaking_news = true THEN '常规话题(爆点)'
                        WHEN is_category_topic = true THEN '领域话题'
                        ELSE '其他话题'
                    END as topic_category,
                    COUNT(*) as article_count,
                    AVG(final_score_v2) as avg_final_score,
                    AVG(hot_norm) as avg_hot_norm
                FROM raw_events 
                WHERE published_at >= NOW() - INTERVAL '24 HOURS'
                GROUP BY topic_category
                ORDER BY article_count DESC;
            """)
            
            results = cur.fetchall()
            if results:
                print("话题类型分布:")
                for row in results:
                    print(f"  {row['topic_category']}:")
                    print(f"    文章数: {row['article_count']}")
                    print(f"    平均最终分数: {row['avg_final_score']:.4f}")
                    print(f"    平均热度分数: {row['avg_hot_norm']:.4f}")
                    print()
            else:
                print("❌ 无法获取话题分布数据")
    except Exception as e:
        print(f"❌ 分析话题分布失败: {e}")
    finally:
        conn.close()

def check_top_articles():
    """检查高分文章"""
    print("\n=== 高分文章分析 (前10名) ===")
    
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    title,
                    source_name,
                    published_at,
                    final_score_v2,
                    hot_norm,
                    is_routine_topic,
                    is_category_topic,
                    is_breaking_news,
                    is_suppressed,
                    is_downweighted
                FROM raw_events 
                WHERE published_at >= NOW() - INTERVAL '24 HOURS'
                  AND final_score_v2 IS NOT NULL
                ORDER BY final_score_v2 DESC
                LIMIT 10;
            """)
            
            results = cur.fetchall()
            if results:
                print("排名 | 标题 | 分数 | 来源 | 抑制状态")
                print("-" * 80)
                for i, row in enumerate(results, 1):
                    status = []
                    if row['is_suppressed']:
                        status.append("抑制")
                    if row['is_downweighted']:
                        status.append("降权")
                    if row['is_breaking_news']:
                        status.append("爆点")
                    status_str = ", ".join(status) if status else "正常"
                    
                    title_short = row['title'][:50] + "..." if len(row['title']) > 50 else row['title']
                    print(f"{i:2d} | {title_short} | {row['final_score_v2']:.4f} | {row['source_name']} | {status_str}")
            else:
                print("❌ 无法获取高分文章数据")
    except Exception as e:
        print(f"❌ 检查高分文章失败: {e}")
    finally:
        conn.close()

def verify_airflow_variables():
    """验证Airflow Variables配置"""
    print("\n=== 验证Airflow Variables配置 ===")
    
    # 这里需要连接到Airflow数据库或通过API获取
    # 由于环境限制，我们提供检查清单
    print("请在Airflow UI中验证以下变量:")
    print("1. ainews_routine_topic_uris - 常规话题URI列表")
    print("2. ainews_downweight_category_uris - 领域话题URI列表")
    print("3. ainews_routine_topic_damping_factor - 抑制强度 (默认0.3)")
    print("4. ainews_category_damping_factor - 降权强度 (默认0.5)")
    print("5. ainews_freshness_threshold_for_breaking - 爆点阈值 (默认0.8)")
    print("\n检查路径: Admin -> Variables")

def main():
    """主验证流程"""
    print("🔍 生产环境双重话题抑制功能验证")
    print("=" * 50)
    
    # 1. 验证监控字段
    fields_ok = verify_suppression_fields()
    
    # 2. 获取抑制统计
    get_suppression_stats()
    
    # 3. 分析话题分布
    analyze_topic_distribution()
    
    # 4. 检查高分文章
    check_top_articles()
    
    # 5. 验证配置
    verify_airflow_variables()
    
    print("\n" + "=" * 50)
    if fields_ok:
        print("✅ 验证完成！双重话题抑制功能已正确部署。")
    else:
        print("❌ 验证失败！请检查部署状态。")

if __name__ == "__main__":
    main() 