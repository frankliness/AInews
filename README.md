# AInews v2.4.1 - 智能新闻处理系统

> 🎉 **最新版本**: v2.4.1 - 系统配置优化版本  
> 📅 **发布日期**: 2025年8月5日  
> 🚀 **主要更新**: 双重话题抑制、调度时间优化、文件输出路径修复

## 🎯 系统概述

AInews v2.4.1 是一个基于 EventRegistry 的智能新闻处理系统，集成了独立的 Phoenix 新闻处理管道。系统通过聚类、打分、话题抑制和自动调参，实现高质量的新闻事件去同质化，为零 GPT 依赖的新闻汇总提供数据基础。

### v2.4.1 新特性
- **双重话题抑制**: 常规话题抑制 + 领域话题降权机制
- **高性能向量化算法**: 提升20-30%处理效率
- **调度时间优化**: 从每天3次改为每天1次运行，减少66%资源消耗
- **文件输出路径修复**: 确保文件输出到正确位置
- **权威分计算修复**: 基于真实信源排名的权威分计算
- **双路并行抓取**: 同时获取热门和突发事件

## 🚀 核心特性

### 1. Phoenix 独立系统
- **独立数据库环境**: 专用的 Phoenix PostgreSQL 数据库
- **高级新闻评分**: 基于机器学习的新闻重要性评分系统
- **智能聚类**: 改进的主题聚类和事件关联算法
- **北京时间支持**: 自动时区转换，确保所有时间数据使用北京时间

### 2. 智能聚类
- **一级聚类**：基于 EventRegistry 的 event_id 进行事件级聚类
- **二级聚类**：对超大事件（>50条）进行细分聚类
- **聚类中心**：计算与聚类中心的余弦相似度

### 3. 五维度打分 + 话题抑制 (v2.4.1 升级)
- **热度分数**：基于时间衰减 + EventRegistry 字段（total_articles_24h、source_importance、wgt）
- **权威分数**：基于真实信源排名（importanceRank）
- **概念热度分数**：基于实体热度评分
- **新鲜分数**：基于时区感知的时效性计算
- **情感分数**：基于情感分析绝对值归一化
- **话题抑制**：常规话题抑制（强度0.3）+ 领域话题降权（强度0.5）
- **综合分数**：五维度加权平均 + 抑制效果

### 4. 自动调参
- **每周自学习**：基于历史数据自动优化参数
- **β_i优化**：热度子权重自动调整
- **w_j优化**：维度混合权重自动调整

### 5. 零GPT依赖
- **纯数据驱动**：基于 EventRegistry 字段进行去同质化
- **可直接生成汇总日志**：为下一环节提供高质量数据

## 📊 系统架构

### 双系统架构

#### Phoenix 系统（v2.4.1 最新）
```
Phoenix 独立环境
├── 专用数据库 (端口 5434)
├── 独立 Airflow (端口 8082)
├── 高级评分算法 + 话题抑制
├── 北京时间支持
└── 优化调度配置
```

#### 主系统（v1.0 兼容）
```
主系统环境
├── 主数据库 (端口 5432)
├── 主 Airflow (端口 8080)
├── 基础评分算法
└── 兼容性支持
```

### 两套并行数据流

#### 方案A：直接数据库流（主要流程）
```
ingestion_scoring_pipeline (22:00)  # v2.4.1优化：每天1次
    ↓ 直接写入数据库 (raw_events表)
summary_generation_dag (23:00)
    ↓ 从数据库读取并处理
聚类 → 打分 → 话题抑制 → 汇总
```

#### 方案B：日志汇总流（保留功能）
```
fetch_eventregistry_news (10:00/17:00/22:00)
    ↓ 写入日志文件 (logs/news/{source}/)
aggregate_daily_logs (00:00)
    ↓ 汇总日志文件
生成汇总文件 (logs/news/summary/)
```

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

## 📁 项目结构（核心）

```
dev/
├── dags/
│   └── phoenix/
│       ├── ingestion_scoring_pipeline_dag.py   # 采集+高级打分
│       ├── summary_generation_dag.py           # 每日摘要生成(JSON)
│       └── advanced_scorer.py / json_report_generator.py
├── docker-compose.phoenix.yml
├── exports/                                    # Phoenix 摘要输出目录
├── docs/
├── scripts/
├── sql/
└── utils/
```

## ⏰ DAG调度配置（北京时间）

| DAG | 功能 | 调度时间 | Cron表达式 | 状态 |
|-----|------|----------|------------|------|
| ingestion_scoring_pipeline | Phoenix新闻采集与打分 | 22:00 | 0 14 * * * | ✅ 活跃 |
| summary_generation_dag | Phoenix摘要生成 | 23:00 | 0 15 * * * | ✅ 活跃 |
| aggregate_daily_logs | 日志汇总（备用流） | 00:00 | 0 0 * * * | ⚠️ 备用 |

## 🗑️ 已下线功能与DAG

下表列出了近期下线/废弃的功能与DAG，以及原因与替代方案，确保读者查阅文档时不走旧路径。

| 名称 | 类型 | 状态 | 下线原因 | 替代方案/说明 |
|---|---|---|---|---|
| fetch_twitter | DAG | 已下线 | 平台限制、信噪比低、维护成本高 | 暂无替代；如需社媒数据，后续以外部数据源导入为准 |
| make_daily_cards | DAG | 已下线 | 与新摘要产出重复 | 使用 `summary_generation_dag` 生成JSON摘要文件 |
| fetch_news | DAG | 已下线 | 旧版抓取与评分已被整合 | 使用 `ingestion_scoring_pipeline` 统一抓取+评分 |
| parse_summary_logs | DAG | 已下线 | 与数据库直读重复 | 日志汇总保留备用：`aggregate_daily_logs`，仅用于调试/审计 |
| pipeline/daily_summary | 功能 | 已下线 | 与 Phoenix 摘要产出重复 | 使用 `summary_generation_dag`（输出至 `dev/exports/`） |

> 提醒：Phoenix 主路径为 `ingestion_scoring_pipeline → DB → summary_generation_dag`。日志汇总流仅作备份用途。

## 🚀 快速开始

### 1. 启动服务
```bash
# 启动Phoenix系统（推荐）
docker-compose -f docker-compose.phoenix.yml up -d

# 检查服务状态
docker-compose -f docker-compose.phoenix.yml ps
```

### 2. 访问Web界面
- **Phoenix Airflow UI**: http://localhost:8082 (用户名: phoenix_admin, 密码: phoenix123)
- **Phoenix PgAdmin**: http://localhost:5051 (用户名: phoenix@example.com, 密码: phoenix123)

### 3. 手动触发DAG
```bash
# 触发Phoenix新闻采集与打分
docker-compose -f docker-compose.phoenix.yml exec phoenix-webserver airflow dags trigger ingestion_scoring_pipeline

# 触发Phoenix摘要生成
docker-compose -f docker-compose.phoenix.yml exec phoenix-webserver airflow dags trigger summary_generation_dag
```

## 📝 文档

- [v2.4.1发布说明](RELEASE_V2.4.1.md) - v2.4.1版本详细发布说明
- [v2.4.0发布说明](RELEASE_V2.4.0.md) - v2.4.0版本详细发布说明
- [版本演进总结](VERSION_SUMMARY.md) - 完整的版本演进历史
- [话题抑制实现文档](docs/topic_suppression_implementation.md) - 双重话题抑制功能实现
- [生产环境验证指南](docs/production_verification_guide.md) - 生产环境验证指南
- [系统架构文档](docs/system_architecture.md) - 详细的系统架构说明
- [日志汇总文档](docs/log_aggregation.md) - 日志汇总流程说明（备用流） 