# Phoenix 新闻处理系统

> 🎉 **当前版本**: Phoenix v2.4.2 - 精简优化版本  
> 📅 **发布日期**: 2025年1月2日  
> 🚀 **核心特性**: 双重话题抑制、智能评分、自动化摘要生成

## 🎯 系统概述

Phoenix 是一个基于 EventRegistry API 的智能新闻处理系统，专注于高质量新闻事件的采集、评分和摘要生成。系统通过先进的话题抑制机制和五维度评分算法，实现新闻内容的智能去重和优先级排序。

### v2.4.2 新特性
- **系统精简优化**: 移除冗余代码和文件，提升系统维护性
- **部署文档重构**: 重写Ubuntu部署指南，基于实际项目结构
- **代码结构优化**: 清理历史遗留文件，专注Phoenix核心功能
- **文档体系完善**: 更新技术文档，提升部署和运维体验
- **版本管理优化**: 简化版本发布流程，覆盖历史版本

### v2.4.1 特性
- **双重话题抑制**: 常规话题抑制 + 领域话题降权机制
- **高性能向量化算法**: 提升20-30%处理效率
- **调度时间优化**: 从每天3次改为每天1次运行，减少66%资源消耗
- **文件输出路径修复**: 确保文件输出到正确位置
- **权威分计算修复**: 基于真实信源排名的权威分计算
- **双路并行抓取**: 同时获取热门和突发事件

## 🚀 核心特性

### 1. 智能新闻采集
- **EventRegistry 集成**: 基于 EventRegistry API 的实时新闻采集
- **多源并行抓取**: 同时获取热门和突发事件
- **智能过滤**: 基于信源白名单的内容过滤机制
- **API 配额管理**: 自动密钥轮换和配额监控

### 2. 五维度评分系统
- **热度分数**: 基于事件文章数量和实体热度的综合热度评分
- **权威分数**: 基于信源重要性排名的权威度评分
- **概念热度分数**: 基于 EventRegistry 概念热度的实体评分
- **新鲜分数**: 基于时区感知的时效性评分
- **情感分数**: 基于情感分析的情感倾向评分
- **综合评分**: 五维度加权平均，支持动态权重调整

### 3. 双重话题抑制
- **常规话题抑制**: 对持续热点话题进行智能降权（强度0.3）
- **领域话题降权**: 对非核心领域新闻进行降权（强度0.5）
- **爆点保护机制**: 通过新鲜度阈值避免误杀重要突发新闻
- **向量化处理**: 高性能批量处理，提升20-30%处理效率

### 4. 自动化摘要生成
- **JSON 格式输出**: 结构化的新闻摘要数据
- **北京时间规则**: 严格按照"北京时间6AM"规则筛选新闻
- **事件去重**: 每个事件最多保留2篇最高分文章
- **实时导出**: 自动输出到 `exports/` 目录

## 📊 系统架构

### Phoenix 核心架构
```
Phoenix 新闻处理系统
├── Web 服务 (端口 8082) - Airflow UI
├── 数据库 (端口 5434) - PostgreSQL
├── 管理界面 (端口 5051) - pgAdmin
├── Redis 缓存
└── 文件导出目录 (exports/)
```

### 数据处理流程
```
EventRegistry API
    ↓ 新闻采集
ingestion_scoring_pipeline (每日 22:00)
    ↓ 五维度评分 + 话题抑制
raw_events 数据表
    ↓ 数据筛选与排序
summary_generation_dag (每日 23:00)  
    ↓ JSON 摘要生成
exports/ 目录
```

### 核心数据表
- **raw_events**: 新闻事件主表，包含所有评分和抑制标记
- **trending_concepts**: 概念热度表，用于实体评分计算

## 🔧 完整流程（Phoenix）

```bash
# 1) 触发Phoenix新闻采集与打分（统一流程）
docker-compose -f docker-compose.phoenix.yml exec phoenix-webserver \
  airflow dags trigger ingestion_scoring_pipeline

# 2) 生成每日摘要JSON（输出到 dev/exports/）
docker-compose -f docker-compose.phoenix.yml exec phoenix-webserver \
  airflow dags trigger summary_generation_dag
```

## 📈 监控指标（Phoenix）

### 抑制效果监控（最近24小时）
```sql
SELECT 
    COUNT(*)                                 AS total_articles_24h,
    COUNT(CASE WHEN is_routine_topic   THEN 1 END) AS routine_topic_articles,
    COUNT(CASE WHEN is_category_topic  THEN 1 END) AS category_topic_articles,
    COUNT(CASE WHEN is_breaking_news   THEN 1 END) AS breaking_news_articles,
    COUNT(CASE WHEN is_suppressed      THEN 1 END) AS suppressed_articles,
    COUNT(CASE WHEN is_downweighted    THEN 1 END) AS downweighted_articles,
    ROUND(COUNT(CASE WHEN is_suppressed   THEN 1 END) * 100.0 / COUNT(*), 2) AS suppression_rate,
    ROUND(COUNT(CASE WHEN is_downweighted THEN 1 END) * 100.0 / COUNT(*), 2) AS downweight_rate
FROM raw_events 
WHERE published_at >= NOW() - INTERVAL '24 HOURS';
```

### 打分分布监控（使用 final_score_v2）
```sql
SELECT 
    COUNT(*) AS total_records,
    COUNT(CASE WHEN final_score_v2 >= 0.6 THEN 1 END) AS high_score_records,
    AVG(final_score_v2) AS avg_score
FROM raw_events 
WHERE final_score_v2 IS NOT NULL 
  AND published_at >= NOW() - INTERVAL '24 HOURS';
```

## 🛠️ 环境配置

### 1. 数据库配置
```bash
# 检查数据库连接
# Phoenix
docker compose -f docker-compose.phoenix.yml exec postgres-phoenix \
  psql -U phoenix_user -d phoenix_db -c "SELECT version();"
```

### 2. EventRegistry API配置
```bash
# 设置API Key
export EVENTREGISTRY_APIKEY=你的API密钥
```

### 3. 依赖安装
```bash
#（开发环境）
docker-compose -f docker-compose.phoenix.yml exec phoenix-webserver \
  pip install -r requirements.txt
```

## 📁 项目结构

```
phoenix/
├── dags/phoenix/                  # Airflow DAG 定义
│   ├── ingestion_scoring_pipeline_dag.py    # 新闻采集与评分
│   ├── summary_generation_dag.py            # 摘要生成
│   ├── advanced_scorer.py                   # 高级评分器
│   ├── json_report_generator.py             # JSON 报告生成器
│   └── db_utils.py                          # 数据库工具
├── scraper/                       # 数据采集模块
│   ├── newsapi_client.py                    # EventRegistry 客户端
│   └── __init__.py
├── exports/                       # 摘要输出目录
├── sql/                          # 数据库脚本
│   ├── create_v2_tables.sql                # 核心表结构
│   └── add_suppression_fields.sql          # 抑制字段
├── docs/                         # 文档目录
├── scripts/                      # 工具脚本
└── docker-compose.phoenix.yml    # Docker 配置
```

## ⏰ DAG调度配置（北京时间）

| DAG | 功能 | 调度时间 | Cron表达式 | 状态 |
|-----|------|----------|------------|------|
| ingestion_scoring_pipeline | 新闻采集与评分 | 22:00 | 0 14 * * * | ✅ 运行中 |
| summary_generation_dag | 摘要生成 | 23:00 | 0 15 * * * | ✅ 运行中 |

**数据流程**: EventRegistry → 采集评分 → 数据库存储 → 摘要生成 → JSON导出

## 🚀 快速开始

### 1. 启动服务
```bash
# 启动Phoenix系统（推荐）
docker-compose -f docker-compose.phoenix.yml up -d

# 检查服务状态
docker-compose -f docker-compose.phoenix.yml ps
```

### 2. 访问Web界面
- **Airflow UI**: http://localhost:8082 (用户名: phoenix_admin, 密码: phoenix123)
- **数据库管理**: http://localhost:5051 (用户名: phoenix@example.com, 密码: phoenix123)

### 3. 手动触发DAG
```bash
# 触发新闻采集与评分
docker-compose -f docker-compose.phoenix.yml exec phoenix-webserver airflow dags trigger ingestion_scoring_pipeline

# 触发摘要生成
docker-compose -f docker-compose.phoenix.yml exec phoenix-webserver airflow dags trigger summary_generation_dag
```

### 4. 查看输出结果
```bash
# 查看生成的摘要文件
ls -la exports/

# 查看最新摘要内容
cat exports/summary_$(date +%Y-%m-%d)_*.json | jq '.'
```

## 📝 文档

- [话题抑制实现](docs/topic_suppression_implementation.md) - 双重话题抑制功能详解
- [生产验证指南](docs/production_verification_guide.md) - 系统功能验证方法
- [部署指南](docs/ubuntu_deployment_guide.md) - Ubuntu服务器部署指南
- [数据库管理](docs/pgadmin_login_guide.md) - 数据库访问和管理 