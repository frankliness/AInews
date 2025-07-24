# 去同质化v2系统 - 基于EventRegistry的智能新闻去重

## 🎯 系统概述

去同质化v2是一个基于EventRegistry字段的智能新闻去重系统，通过聚类、打分和自动调参，实现高质量的新闻事件去同质化，为零GPT依赖的新闻汇总提供数据基础。

## 🚀 核心特性

### 1. 智能聚类
- **一级聚类**：基于EventRegistry的event_id进行事件级聚类
- **二级聚类**：对超大事件（>50条）进行细分聚类
- **聚类中心**：计算与聚类中心的余弦相似度

### 2. 三维度打分
- **热度分数**：基于时间衰减 + EventRegistry字段（total_articles_24h、source_importance、wgt）
- **代表性分数**：基于聚类中心相似度
- **情感分数**：基于情感分析绝对值归一化
- **综合分数**：三维度加权平均

### 3. 自动调参
- **每周自学习**：基于历史数据自动优化参数
- **β_i优化**：热度子权重自动调整
- **w_j优化**：维度混合权重自动调整

### 4. 零GPT依赖
- **纯数据驱动**：基于EventRegistry字段进行去同质化
- **可直接生成汇总日志**：为下一环节提供高质量数据

## 📊 系统架构

### 两套并行数据流

#### 方案A：直接数据库流（主要流程）
```
fetch_eventregistry_news (10:00/17:00/22:00)
    ↓ 直接写入数据库 (raw_events表)
jiuwanli_daily (23:00)
    ↓ 从数据库读取并处理
聚类 → 打分 → 采样 → 汇总
```

#### 方案B：日志汇总流（保留功能）
```
fetch_eventregistry_news (10:00/17:00/22:00)
    ↓ 写入日志文件 (logs/news/{source}/)
aggregate_daily_logs (00:00)
    ↓ 汇总日志文件
生成汇总文件 (logs/news/summary/)
```

## 🔧 完整流程

### 1. 数据采集阶段
```bash
# 触发EventRegistry新闻采集
docker compose exec airflow-webserver airflow dags trigger fetch_eventregistry_news
```

**采集内容**：
- 新闻标题、正文、URL、发布时间
- EventRegistry字段：event_id、embedding、total_articles_24h、source_importance、wgt
- 情感分析：sentiment

**数据存储**：`raw_events` 表

### 2. 聚类阶段
```bash
# 执行主题聚类
docker compose exec airflow-webserver python -c "
import os; os.environ['DATABASE_URL'] = 'postgresql://airflow:airflow_pass@postgres:5432/ainews';
from pipeline.cluster_topics import run; run()
"
```

**聚类逻辑**：
- 基于event_id进行一级聚类
- 对超大事件进行二级细分聚类
- 计算聚类中心相似度
- 更新topic_id、cluster_size、centroid_sim字段

### 3. 打分阶段
```bash
# 执行新闻打分
docker compose exec airflow-webserver python -c "
import os; os.environ['DATABASE_URL'] = 'postgresql://airflow:airflow_pass@postgres:5432/ainews';
from pipeline.score import run; run()
"
```

**打分维度**：
- 热度分数：时间衰减 + EventRegistry字段
- 代表性分数：聚类中心相似度
- 情感分数：情感分析绝对值
- 综合分数：三维度加权平均

### 4. 采样阶段
```bash
# 执行高分新闻采样
docker compose exec airflow-webserver python -c "
import os; os.environ['DATABASE_URL'] = 'postgresql://airflow:airflow_pass@postgres:5432/ainews';
from pipeline.sample import run; run()
"
```

**采样逻辑**：
- 按分数排序选择top_k新闻
- 确保事件多样性（每个topic_id最多选择1条）
- 生成daily_cards表

### 5. 汇总文档生成
```bash
# 生成汇总文档
docker compose exec airflow-webserver python -c "
import os; os.environ['DATABASE_URL'] = 'postgresql://airflow:airflow_pass@postgres:5432/ainews';
from pipeline.summarize import run; run()
"
```

**汇总内容**：
- 基于daily_cards中的高分新闻
- 生成结构化汇总文档
- 输出到exports目录

## 📈 监控指标

### 聚类效果监控
```sql
SELECT 
    COUNT(DISTINCT topic_id) as unique_topics,
    AVG(cluster_size) as avg_cluster_size,
    MAX(cluster_size) as max_cluster_size
FROM raw_events 
WHERE topic_id IS NOT NULL 
  AND published_at >= NOW() - INTERVAL '24 HOURS';
```

### 打分分布监控
```sql
SELECT 
    COUNT(*) as total_records,
    COUNT(CASE WHEN score >= 0.6 THEN 1 END) as high_score_records,
    AVG(score) as avg_score
FROM raw_events 
WHERE score IS NOT NULL 
  AND published_at >= NOW() - INTERVAL '24 HOURS';
```

## 🛠️ 环境配置

### 1. 数据库配置
```bash
# 检查数据库连接
docker compose exec postgres psql -U airflow -d ainews -c "SELECT version();"
```

### 2. EventRegistry API配置
```bash
# 设置API Key
export EVENTREGISTRY_APIKEY=你的API密钥
```

### 3. 依赖安装
```bash
# 安装机器学习依赖
docker compose exec airflow-webserver pip install -r requirements-dedup.txt
```

## 📁 项目结构

```
dev/
├── dags/                          # Airflow DAG文件
│   ├── fetch_eventregistry_news.py    # 新闻采集DAG（3次/天）
│   ├── jiuwanli_daily.py             # 时政视频账号每日处理DAG（1次/天）
│   ├── jiuwanli_weekly_tune.py       # 时政视频账号周度调参DAG（1次/周）
│   ├── aggregate_daily_logs.py       # 日志汇总DAG（1次/天，保留功能）
│   └── analyze_daily_sentiment.py    # 情感分析DAG（1次/天）
├── pipeline/                       # 核心算法模块
│   ├── cluster_topics.py             # 主题聚类
│   ├── score.py                     # 新闻打分
│   ├── auto_tune.py                 # 自动调参
│   └── sample.py                    # 高分采样
├── scraper/                        # 数据采集模块
│   ├── base_newsapi.py              # EventRegistry集成
│   └── base.py                      # 基础类定义
├── utils/                          # 工具函数
│   └── text.py                      # 文本处理工具
├── config.yaml                     # 配置文件
├── requirements-dedup.txt          # 依赖文件
└── exports/                        # 输出目录
    └── cluster_score_export.csv    # 聚类打分结果
```

## ⏰ DAG调度配置（北京时间）

| DAG | 功能 | 调度时间 | Cron表达式 | 状态 |
|-----|------|----------|------------|------|
| fetch_eventregistry_news | 多源新闻抓取 | 10:00/17:00/22:00 | 0 2,9,14 * * * | ✅ 活跃 |
| jiuwanli_daily | 时政视频账号去同质化核心流程 | 23:00 | 0 15 * * * | ✅ 活跃 |
| aggregate_daily_logs | 日志汇总 | 00:00 | 0 0 * * * | ✅ 活跃 |
| jiuwanli_weekly_tune | 时政视频账号周度自动调参 | 每周一11:00 | 0 3 * * MON | ✅ 活跃 |
| analyze_daily_sentiment | 情感分析 | 每天 | @daily | ✅ 活跃 |

## 🗑️ 已删除DAG

- `fetch_twitter` - Twitter推文抓取
- `make_daily_cards` - 选题卡片生成
- `fetch_news` - 旧版新闻抓取
- `parse_summary_logs` - 重复的日志解析ETL

## 🎯 使用场景

### 1. 新闻去重
- 基于EventRegistry事件ID进行智能去重
- 避免重复报道同一事件
- 提高新闻汇总质量

### 2. 热点发现
- 通过打分系统识别热点新闻
- 基于多维度的智能排序
- 自动发现重要事件

### 3. 内容聚合
- 为新闻汇总提供高质量数据源
- 支持零GPT依赖的内容生成
- 提供结构化的新闻数据

## 📊 效果评估

### 当前测试结果
- **聚类效果**：25个唯一事件，每个事件1条新闻
- **打分分布**：平均分0.056，高分新闻25条（1.7%）
- **系统稳定性**：所有核心模块100%通过测试

## 🎯 简化后的优势

### 1. **消除重复处理**
- 移除了 `parse_summary_logs` 这个重复的数据库写入步骤
- 减少了不必要的数据转换和存储操作

### 2. **提升效率**
- 主要流程直接从数据库读取，减少文件I/O操作
- 减少了数据处理的中间环节

### 3. **双保险保障**
- 保留了两套数据流，确保数据完整性
- 日志汇总功能仍然保留，便于调试和监控

### 4. **架构更清晰**
- 数据流向更加直观
- 减少了DAG之间的复杂依赖关系

## 🚀 快速开始

### 1. 启动服务
```bash
# 启动所有服务
docker-compose up -d

# 检查服务状态
docker-compose ps
```

### 2. 访问Web界面
- **Airflow Web UI**: http://localhost:8080
- **PgAdmin**: http://localhost:5050
- **默认登录**: airflow / airflow

### 3. 手动触发DAG
```bash
# 触发新闻采集
docker compose exec airflow-webserver airflow dags trigger fetch_eventregistry_news

# 触发每日处理
docker compose exec airflow-webserver airflow dags trigger jiuwanli_daily
```

## 📝 文档

- [系统架构文档](docs/system_architecture.md) - 详细的系统架构说明
- [日志汇总文档](docs/log_aggregation.md) - 日志汇总流程说明
- [Twitter优化文档](docs/twitter_optimization.md) - Twitter相关优化说明
- [清理总结文档](CLEANUP_SUMMARY_FINAL.md) - 项目清理和简化总结 