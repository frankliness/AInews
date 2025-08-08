# 新闻日志汇总功能

> 重要：自 v2.4.1 起，日志汇总仅作为【备用数据流/调试用途】，不再作为生产产出路径。生产摘要请使用 `summary_generation_dag`（输出到 `dev/exports/`）。`parse_summary_logs` DAG 已下线；保留的 `aggregate_daily_logs` 仅用于调试/审计。

## 📋 架构说明

**日志汇总功能在简化架构中作为备用数据流保留，用于监控和调试目的。**

### 当前架构中的角色
- **主要数据流**：`fetch_eventregistry_news` → 数据库 → `jiuwanli_daily`
- **备用数据流**：`fetch_eventregistry_news` → 日志文件 → `aggregate_daily_logs`（本功能）

### 功能保留原因
1. **监控调试**：提供完整的日志记录用于问题排查
2. **数据备份**：作为数据库数据的备份和验证
3. **历史追溯**：保留详细的历史数据用于分析

## 概述

新闻日志汇总功能将所有新闻和推文抓取日志按日期汇总到统一目录，提供两种格式的汇总文件：
- 文本格式：`logs/news/summary/summary_YYYY-MM-DD.log`
- JSON格式：`logs/news/summary/summary_YYYY-MM-DD.json`

## 功能特性

### 1. 自动汇总
- 每次记录新闻或推文日志时自动触发汇总
- 支持所有新闻源：Reuters、BBC、CNN、AP、Bloomberg、Financial Times、The Guardian、The New York Times、USA Today、The Washington Post、NPR、Politico、Reuters Business
- 支持Twitter推文日志（只包含真正的推文数据）

### 2. 智能过滤
- **推文日志过滤**：只汇总包含 `text` 字段且不包含 `event_type` 字段的推文
- **系统事件分流**：用户跳过、限速等事件写入 `logs/system/` 目录
- **时区处理**：所有汇总时间使用北京时间（Asia/Shanghai）

### 3. 汇总内容
- **文本格式**：包含所有数据源的日志内容，按源分类
- **JSON格式**：结构化数据，便于程序处理
- 包含汇总统计信息：数据源数量、日志条数等

### 4. 目录结构
```
logs/
├── news/                      # 新闻抓取日志
│   ├── summary/              # 汇总目录
│   │   ├── summary_2025-07-10.log
│   │   └── summary_2025-07-10.json
│   ├── reuters/              # Reuters新闻日志
│   ├── bbc/                  # BBC新闻日志
│   ├── twitter/              # Twitter推文日志
│   ├── cnn/                  # CNN新闻日志
│   ├── ap/                   # AP新闻日志
│   └── ...                   # 其他新闻源
└── system/                   # 系统事件日志
    ├── twitter_activity/     # 用户活跃度日志
    └── twitter_quota/        # 限速事件日志
```

## 使用方法

### 1. 自动汇总
系统会在每次抓取新闻或推文时自动触发汇总，无需手动操作。

### 2. 手动汇总
使用独立脚本进行手动汇总：

```bash
# 汇总指定日期
python -m scraper.log_aggregator --date 2025-07-10

# 汇总最近7天
python -m scraper.log_aggregator --days 7

# 汇总最近1天（默认）
python -m scraper.log_aggregator
```

### 3. 查看汇总文件
```bash
# 查看文本汇总
head -50 logs/news/summary/summary_2025-07-10.log

# 查看JSON汇总
head -20 logs/news/summary/summary_2025-07-10.json

# 查看系统日志
ls -la logs/system/
```

## 汇总文件格式

### 文本格式示例
```
=== 新闻抓取日志汇总 2025-07-10 ===
汇总时间: 2025-07-10 14:02:33
数据源数量: 13

--- TWITTER ---
日志条数: 1
--------------------------------------------------
[1] {"collected_at": "2025-07-10T01:54:22.000951+00:00", "published_at": "2025-07-10T01:37:03+00:00", "username": "", "text": "In a declaration signed Wednesday...", "retweet_count": 32, "reply_count": 34, "like_count": 223, "quote_count": 9, "impression_count": 25390}

--- BBC ---
日志条数: 1
--------------------------------------------------
[1] {"collected_at": "2025-07-10T02:20:10.021493+00:00", "published_at": "2025-07-10T02:15:00+00:00", "title": "BBC News Article", "body": "Article content...", "url": "https://bbc.com/article", "sentiment": 0.2, "weight": 100, "relevance": 0.8}
```

### JSON格式示例
```json
{
  "date": "2025-07-10",
  "aggregated_at": "2025-07-10T14:02:33.841000+08:00",
  "total_sources": 13,
  "sources": {
    "twitter": {
      "log_count": 1,
      "logs": ["{...}"]
    },
    "bbc": {
      "log_count": 1,
      "logs": ["{...}"]
    }
  }
}
```

## 技术实现

### 1. 核心组件
- `LogAggregator`：日志汇总器类
- `log_news_record_with_aggregation`：带汇总的新闻日志记录
- `log_tweet_record_with_aggregation`：带汇总的推文日志记录

### 2. 汇总流程
1. 扫描 `logs/news/` 目录下的所有新闻源
2. 按日期匹配日志文件
3. 读取并合并所有日志内容
4. 过滤非推文数据（包含 `event_type` 字段的日志）
5. 生成文本和JSON格式的汇总文件

### 3. 时区处理
- 所有汇总时间使用北京时间（Asia/Shanghai）
- 使用 `zoneinfo.ZoneInfo('Asia/Shanghai')` 进行时区转换
- 确保日志时间显示的一致性

### 4. 错误处理
- 文件读取失败时记录警告日志
- 汇总失败时不影响正常日志记录
- 支持部分源缺失的情况
- 自动过滤无效的JSON日志行

## 日志分流机制

### 1. 推文日志过滤
```python
def is_tweet_log(line):
    try:
        data = json.loads(line)
        return ("text" in data) and (not data.get("event_type")) and data["text"].strip()
    except Exception:
        return False
```

### 2. 系统事件分流
- **用户跳过事件**：写入 `logs/system/twitter_activity/`
- **限速事件**：写入 `logs/system/twitter_quota/`
- **推文日志**：只包含真正的推文数据

## 测试

运行测试脚本验证功能：
```bash
# 测试日志汇总
python -m scraper.log_aggregator --date $(date +%Y-%m-%d)

# 查看汇总结果
cat logs/news/summary/summary_$(date +%Y-%m-%d).log
```

## 注意事项

1. **文件大小**：汇总文件可能较大，建议定期清理
2. **性能影响**：自动汇总会增加少量I/O开销
3. **存储空间**：汇总文件会占用额外存储空间
4. **兼容性**：保持与现有日志格式的兼容性
5. **时区一致性**：所有时间显示均使用北京时间

## 未来改进

1. **压缩存储**：对汇总文件进行压缩
2. **增量汇总**：只汇总新增的日志内容
3. **定时清理**：自动清理过期的汇总文件
4. **可视化界面**：提供Web界面查看汇总数据
5. **实时监控**：提供实时日志监控功能 