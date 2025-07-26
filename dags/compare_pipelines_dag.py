from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.exceptions import AirflowFailException
import logging

def run_pipeline_comparison(**context):
    """
    裁判系统核心函数：对比V1和V2新闻分析系统的表现
    """
    log = logging.getLogger(__name__)
    log.info("🏁 开始执行Pipeline对比分析")
    
    # 第二阶段：实现核心对比逻辑
    # 2.1 - 创建数据库连接
    log.info("🔗 创建数据库连接")
    legacy_hook = PostgresHook(postgres_conn_id='postgres_default')
    phoenix_hook = PostgresHook(postgres_conn_id='postgres_phoenix_shadow')
    
    # 2.2 - 从两个系统中获取Top 20榜单
    log.info("📊 获取V1系统榜单 (Legacy)")
    legacy_sql = """
        SELECT title FROM public.raw_events 
        WHERE published_at >= NOW() - INTERVAL '24 hours' 
        ORDER BY score DESC 
        LIMIT 20;
    """
    legacy_results = legacy_hook.get_records(legacy_sql)
    
    log.info("📊 获取V2系统榜单 (Phoenix)")
    phoenix_sql = """
        SELECT title FROM phoenix_shadow.raw_events 
        WHERE published_at >= NOW() - INTERVAL '24 hours' 
        ORDER BY (weight * relevance) DESC 
        LIMIT 20;
    """
    phoenix_results = phoenix_hook.get_records(phoenix_sql)
    
    # 数据清洗：转换为set
    legacy_titles = {row[0] for row in legacy_results} if legacy_results else set()
    phoenix_titles = {row[0] for row in phoenix_results} if phoenix_results else set()
    
    log.info(f"📈 V1系统获取到 {len(legacy_titles)} 条新闻")
    log.info(f"📈 V2系统获取到 {len(phoenix_titles)} 条新闻")
    
    # 2.3 - 计算重合度并设置SLA
    if not phoenix_titles:
        overlap_ratio = 0.0
        log.warning("⚠️ V2系统无数据，重合度设为0")
    else:
        overlap_count = len(legacy_titles.intersection(phoenix_titles))
        overlap_ratio = overlap_count / len(phoenix_titles)
        log.info(f"🔄 重合新闻数量: {overlap_count}")
    
    # 第三阶段：生成人类可读的对比报告
    log.info("📋 --- Pipeline Comparison Report ---")
    log.info("=" * 80)
    
    # 基础统计信息
    log.info("📊 基础统计信息:")
    log.info(f"   • V1系统数据量: {len(legacy_titles)} 条新闻")
    log.info(f"   • V2系统数据量: {len(phoenix_titles)} 条新闻")
    log.info(f"   • 重合新闻数量: {len(legacy_titles.intersection(phoenix_titles))}")
    log.info(f"   • 重合度比例: {overlap_ratio:.2%}")
    log.info(f"   • SLA阈值: 30%")
    log.info(f"   • 状态: {'✅ 通过' if overlap_ratio >= 0.3 else '❌ 失败'}")
    
    # 详细分析
    log.info("")
    log.info("🔍 详细分析:")
    if overlap_ratio > 0:
        common_titles = legacy_titles.intersection(phoenix_titles)
        log.info(f"   • 重合新闻列表:")
        for i, title in enumerate(common_titles, 1):
            log.info(f"     {i}. {title}")
    else:
        log.info("   • 无重合新闻")
    
    # V1独有新闻
    v1_only = legacy_titles - phoenix_titles
    log.info(f"   • V1独有新闻: {len(v1_only)} 条")
    if v1_only:
        log.info("   • V1独有新闻示例:")
        for i, title in enumerate(list(v1_only)[:5], 1):
            log.info(f"     {i}. {title}")
        if len(v1_only) > 5:
            log.info(f"     ... 还有 {len(v1_only) - 5} 条")
    
    # V2独有新闻
    v2_only = phoenix_titles - legacy_titles
    log.info(f"   • V2独有新闻: {len(v2_only)} 条")
    if v2_only:
        log.info("   • V2独有新闻示例:")
        for i, title in enumerate(list(v2_only)[:5], 1):
            log.info(f"     {i}. {title}")
        if len(v2_only) > 5:
            log.info(f"     ... 还有 {len(v2_only) - 5} 条")
    
    # 创建并排对比表格
    legacy_list = list(legacy_titles)[:20]
    phoenix_list = list(phoenix_titles)[:20]
    
    log.info("")
    log.info("📰 Top 20 新闻对比表格:")
    log.info("=" * 110)
    log.info(f"{'排名':<4} {'V1 System (Legacy)':<50} {'V2 System (Phoenix)':<50}")
    log.info("-" * 110)
    
    for i in range(20):
        rank = i + 1
        v1_title = legacy_list[i] if i < len(legacy_list) else "N/A"
        v2_title = phoenix_list[i] if i < len(phoenix_list) else "N/A"
        
        # 截断过长标题
        v1_display = (v1_title[:47] + "...") if len(v1_title) > 50 else v1_title
        v2_display = (v2_title[:47] + "...") if len(v2_title) > 50 else v2_title
        
        # 标记重合的新闻
        v1_marker = "🔄" if v1_title in phoenix_titles else " "
        v2_marker = "🔄" if v2_title in legacy_titles else " "
        
        log.info(f"{rank:<4} {v1_marker}{v1_display:<49} {v2_marker}{v2_display:<49}")
    
    log.info("=" * 110)
    log.info("图例: 🔄 = 重合新闻")
    
    # 建议和总结
    log.info("")
    log.info("💡 建议和总结:")
    if overlap_ratio < 0.3:
        log.info("   • 重合度过低，建议:")
        log.info("     - 检查两个系统的数据源配置")
        log.info("     - 验证评分算法的一致性")
        log.info("     - 考虑调整SLA阈值")
        log.info("     - 分析数据抓取时间窗口")
    else:
        log.info("   • 系统表现良好，重合度符合预期")
    
    log.info(f"   • 下次检查时间: 明天 {datetime.now().strftime('%H:%M')}")
    log.info("=" * 80)
    
    # SLA检查 - 如果重合度低于30%则失败
    if overlap_ratio < 0.3:
        error_msg = f"❌ Pipeline results have diverged too much! Overlap is only {overlap_ratio:.2%} (< 30%)"
        log.error(error_msg)
        raise AirflowFailException(error_msg)
    
    log.info(f"✅ 系统对比通过! 重合度: {overlap_ratio:.2%} (>= 30%)")
    return f"Comparison completed successfully. Overlap: {overlap_ratio:.2%}"

# DAG定义
default_args = {
    'owner': 'data_team',
    'depends_on_past': False,
    'start_date': datetime(2025, 7, 26),
    'email_on_failure': False,  # 暂时禁用邮件警报
    'email_on_retry': False,
    'email': ['admin@example.com'],  # 保留配置，未来可启用
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'compare_pipelines_daily',
    default_args=default_args,
    description='Daily comparison between V1 and V2 news analysis pipelines',
    schedule_interval='@daily',
    catchup=False,
    tags=['monitoring', 'comparison', 'v1', 'v2'],
)

# 第四阶段：创建PythonOperator
run_ab_comparison_task = PythonOperator(
    task_id='run_ab_comparison_task',
    python_callable=run_pipeline_comparison,
    sla=timedelta(minutes=30),
    dag=dag,
) 