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

| DAG | 功能 | 调度时间 | Cron表达式 | 备注 |
|-----|------|----------|------------|------|
| ingestion_scoring_pipeline | Phoenix新闻采集与打分 | 22:00 | 0 14 * * * | v2.4.1 优化为每日一次 |
| summary_generation_dag | Phoenix摘要生成 | 23:00 | 0 15 * * * | 输出到 `dev/exports/` |
| aggregate_daily_logs | 日志汇总（备用流） | 00:00 | 0 0 * * * | 仅用于调试/审计，不参与产出 |

## 🔄 工作流（现网主路径）
```
ingestion_scoring_pipeline (22:00)
  → 写入 DB(raw_events)
summary_generation_dag (23:00)
  → 从 DB 读取 → 生成 JSON 摘要 → dev/exports/
```

## 🎯 简化后的优势

1. **消除重复**：移除了 `parse_summary_logs` 这个重复的数据库写入步骤
2. **双保险**：保留了两套数据流，确保数据完整性
3. **效率提升**：主要流程直接从数据库读取，减少文件I/O
4. **功能保留**：日志汇总功能仍然保留，便于调试和监控

## 🗑️ 已下线/已删除DAG
- fetch_twitter（Twitter推文抓取）→ 已下线。原因：平台限制、信噪比低。替代：无，必要时外部导入。
- make_daily_cards（选题卡片生成）→ 已下线。替代：`summary_generation_dag`。
- fetch_news（旧版新闻抓取）→ 已下线。替代：`ingestion_scoring_pipeline` 统一抓取+评分。
- parse_summary_logs（重复的日志解析ETL）→ 已下线。替代：保留 `aggregate_daily_logs` 仅作调试/审计。

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