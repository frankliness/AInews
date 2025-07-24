# 汇总日志ETL流程（已删除）

## ⚠️ 重要说明

**该ETL流程已于2025-07-16删除，作为架构简化的一部分。**

## 🎯 删除原因

### 重复处理问题
原来的流程存在重复的数据处理步骤：
1. `fetch_eventregistry_news` 直接写入数据库
2. `aggregate_daily_logs` 从日志文件汇总
3. `parse_summary_logs` 又把汇总文件写回数据库

这造成了不必要的数据转换和存储操作。

## 🔄 新的简化架构

### 方案A：直接数据库流（主要流程）
```
fetch_eventregistry_news (10:00/17:00/22:00)
    ↓ 直接写入数据库 (raw_events表)
jiuwanli_daily (23:00)
    ↓ 从数据库读取并处理
聚类 → 打分 → 采样 → 汇总
```

### 方案B：日志汇总流（保留功能）
```
fetch_eventregistry_news (10:00/17:00/22:00)
    ↓ 写入日志文件 (logs/news/{source}/)
aggregate_daily_logs (00:00)
    ↓ 汇总日志文件
生成汇总文件 (logs/news/summary/)
```

## ✅ 简化后的优势

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

## 📊 当前系统状态

### 活跃DAG列表（5个）
| DAG | 功能 | 调度时间 | 状态 |
|-----|------|----------|------|
| fetch_eventregistry_news | 多源新闻抓取 | 10:00/17:00/22:00 | ✅ 活跃 |
| jiuwanli_daily | 时政视频账号去同质化核心流程 | 23:00 | ✅ 活跃 |
| aggregate_daily_logs | 日志汇总 | 00:00 | ✅ 活跃 |
| jiuwanli_weekly_tune | 时政视频账号周度自动调参 | 每周一11:00 | ✅ 活跃 |
| analyze_daily_sentiment | 情感分析 | 每天 | ✅ 活跃 |

### 已删除DAG（4个）
- `fetch_twitter` - Twitter推文抓取
- `make_daily_cards` - 选题卡片生成
- `fetch_news` - 旧版新闻抓取
- `parse_summary_logs` - 重复的日志解析ETL

## 🔧 数据流向说明

### 主要数据流（方案A）
1. **数据采集**：`fetch_eventregistry_news` 直接从EventRegistry API获取新闻并写入数据库
2. **数据处理**：`jiuwanli_daily` 从数据库读取数据进行聚类、打分、采样
3. **结果输出**：生成汇总文档和导出文件

### 备用数据流（方案B）
1. **日志记录**：`fetch_eventregistry_news` 同时写入日志文件
2. **日志汇总**：`aggregate_daily_logs` 汇总日志文件生成汇总文件
3. **监控调试**：汇总文件用于监控和调试目的

## 📝 相关文档

- [系统架构文档](system_architecture.md) - 详细的系统架构说明
- [清理总结文档](../CLEANUP_SUMMARY_FINAL.md) - 项目清理和简化总结
- [最终实施总结](../DEDUP_V2_FINAL_SUMMARY.md) - 完整的实施总结

---

**注意**：此文档保留作为历史参考，实际系统已采用简化的架构。 