# 去同质化v2系统架构文档

## 🏗️ 项目结构

```
dev/
├── dags/                # Airflow DAG文件
│   ├── pipeline/        # 核心处理模块
│   │   ├── cluster_topics.py   # 主题聚类
│   │   ├── score.py           # 新闻打分
│   │   ├── auto_tune.py       # 自动调参
│   │   └── daily_summary.py   # 每日汇总
│   ├── fetch_eventregistry_news.py  # 多源新闻抓取
│   ├── jiuwanli_daily.py      # 时政视频账号去同质化核心流程
│   ├── jiuwanli_weekly_tune.py # 时政视频账号周度自动调参
│   ├── aggregate_daily_logs.py # 日志汇总（保留功能）
│   └── analyze_daily_sentiment.py # 情感分析
├── scraper/             # 新闻抓取器（13源+Twitter相关代码保留）
├── utils/               # 工具函数
├── docs/                # 文档
├── logs/                # 日志文件
├── exports/             # 输出文件
├── sql/                 # SQL脚本
└── pipeline/            # 核心算法模块
```

## ⏰ DAG调度配置（北京时间）

| DAG | 功能 | 调度时间 | Cron表达式 |
|-----|------|----------|------------|
| aggregate_daily_logs | 汇总前一日日志 | 00:00 | 0 0 * * * |
| fetch_eventregistry_news | 多源新闻抓取 | 10:00/17:00/22:00 | 0 2,9,14 * * * |
| jiuwanli_daily | 时政视频账号去同质化核心流程 | 23:00 | 0 15 * * * |
| jiuwanli_weekly_tune | 时政视频账号周度自动调参 | 每周一11:00 | 0 3 * * MON |
| analyze_daily_sentiment | 情感分析 | 每天 | @daily |

## 🔄 工作流数据流（两套并行）

### 方案A：直接数据库流（主要流程）
```
fetch_eventregistry_news (10:00/17:00/22:00)
    ↓ 直接写入数据库
jiuwanli_daily (23:00)
    ↓ 从数据库读取并处理
聚类 → 打分 → 采样 → 汇总
```

### 方案B：日志汇总流（保留功能）
```
fetch_eventregistry_news (10:00/17:00/22:00)
    ↓ 写入日志文件
aggregate_daily_logs (00:00)
    ↓ 汇总日志文件
生成汇总文件 (logs/news/summary/)
```

## 🎯 简化后的优势

1. **消除重复**：移除了 `parse_summary_logs` 这个重复的数据库写入步骤
2. **双保险**：保留了两套数据流，确保数据完整性
3. **效率提升**：主要流程直接从数据库读取，减少文件I/O
4. **功能保留**：日志汇总功能仍然保留，便于调试和监控

## 🗑️ 已废弃/已删除DAG
- fetch_twitter（Twitter推文抓取，已删除）
- make_daily_cards（选题卡片生成，已删除）
- fetch_news（旧版新闻抓取，已删除）
- parse_summary_logs（重复的日志解析ETL，已删除）

## 📈 系统特点
- 模块化设计，数据采集、处理、分析分离
- 自动化流程，从数据采集到最终输出全自动化
- 智能去同质化，基于机器学习的新闻去重和聚类
- 自动调参，每周基于历史数据优化参数
- 完整监控，从数据采集到结果输出的全链路监控
- 双数据流保障，确保数据完整性和系统可靠性

## 依赖与环境
- 详见 requirements.txt
- Docker部署，所有核心目录已正确挂载

## 当前状态
- 简化后的架构更加高效，消除了重复处理
- 保留了两套数据流，确保系统稳定性
- 所有DAG与文档已同步，结构清晰，便于维护与扩展 