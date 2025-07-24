# Twitter 抓取器优化功能文档

## ⚠️ 重要说明

**Twitter抓取DAG（`fetch_twitter`）已于2025-07-16删除，但相关代码和功能保留用于未来可能的重新启用。**

### 当前状态
- ✅ **代码保留**：所有Twitter相关代码保留在`scraper/`目录中
- ✅ **功能完整**：优化功能、日志分流、时区处理等功能完整保留
- ✅ **随时可用**：可以随时重新启用Twitter抓取功能
- ❌ **DAG删除**：`fetch_twitter` DAG已从Airflow中删除

### 保留原因
1. **功能完整性**：Twitter抓取功能经过充分优化，具有重要价值
2. **未来需求**：可能在未来需要重新启用Twitter数据抓取
3. **技术参考**：作为高质量数据抓取功能的参考实现
4. **快速恢复**：可以快速重新启用，无需重新开发

## 概述

本次优化实现了高效的限速优先级与抓取策略，大幅提升了 Twitter 数据抓取的效率和覆盖面，并实现了智能日志分流和时区处理。

## 核心优化功能

### 1. 拉取策略优化

#### 单次请求最大化
- **固定 `max_results=100`**：使用 Twitter API v2 允许的最大值
- **启用分页**：自动处理 `next_token`，连续翻页直到达到限制

#### 分页上限控制
- **每用户最多 5 页**：防止单个用户占用过多配额
- **总计 500 条推文**：`MAX_RESULTS_PER_REQUEST * MAX_PAGES_PER_USER`

#### 用户循环策略
- **活跃用户列表**：维护 User ID 数组，按顺序遍历
- **限速跳过**：遇到限速立即切换到下一个用户
- **最大化覆盖面**：确保一小时内能覆盖所有用户

### 2. 限速检测与处理

#### 动态监控 API 头
```python
def _parse_rate_limit_headers(response: requests.Response) -> RateLimitInfo:
    remaining = int(response.headers.get('x-rate-limit-remaining', 0))
    reset_time = int(response.headers.get('x-rate-limit-reset', 0))
    limit = int(response.headers.get('x-rate-limit-limit', 0))
```

#### 限速触发条件
- `x-rate-limit-remaining` ≤ 1
- 收到 429/403 状态码
- 立即触发"限速逻辑"

#### 限速处理策略
- **当前用户终止**：停止后续分页与重试
- **立即切换用户**：不等待重置时间
- **记录限速事件**：写入系统日志

### 3. 增量抓取与去重

#### since_id 增量抓取
- **用户进度管理**：为每个用户维护 `since_id`
- **避免重复调用**：只获取上次抓取后的新推文
- **进度持久化**：保存到 `logs/news/twitter/user_progress.json`

#### 数据库级去重
- **Tweet ID 唯一**：已写入数据库的推文不再存储
- **日志级去重**：避免重复记录到日志文件

### 4. 智能日志分流

#### 推文日志过滤
- **只记录真正推文**：包含 `text` 字段且不包含 `event_type` 字段
- **推文日志位置**：`logs/news/twitter/twitter_YYYY-MM-DD.log`

#### 系统事件分流
- **用户跳过事件**：写入 `logs/system/twitter_activity/twitter_activity_YYYY-MM-DD.log`
- **限速事件**：写入 `logs/system/twitter_quota/twitter_quota_YYYY-MM-DD.log`
- **窗口耗尽事件**：写入 `logs/system/twitter_quota/twitter_quota_YYYY-MM-DD.log`

### 5. 时区处理
- **北京时间显示**：所有日志时间使用 Asia/Shanghai 时区
- **24小时过滤**：基于北京时间进行时间过滤
- **日志归档**：06:00 前归档到前一天日志文件

## 配置常量

```python
MAX_RESULTS_PER_REQUEST = 100  # Twitter API v2 单次请求最大值
MAX_PAGES_PER_USER = 5         # 每用户最多连续翻页数
MAX_TWEETS_PER_USER = 500      # 每用户最大推文数
```

## 数据结构

### RateLimitInfo
```python
@dataclass
class RateLimitInfo:
    remaining: int
    reset_time: Optional[int] = None
    limit: Optional[int] = None
```

### UserProgress
```python
@dataclass
class UserProgress:
    user_id: str
    username: str
    since_id: Optional[str] = None
    last_tweet_id: Optional[str] = None
    pages_fetched: int = 0
    tweets_fetched: int = 0
```

## 验收标准验证

### ✅ 单请求条数
- **恒为 100**：`MAX_RESULTS_PER_REQUEST = 100`

### ✅ 限速触发处理
- **立即切换用户**：遇到限速立即停止当前用户，切换到下一个
- **任务不中断**：整个抓取任务继续运行

### ✅ 一小时覆盖
- **所有用户列表**：一小时内能覆盖所有配置的用户
- **跳过记录**：因限速未覆盖的用户会记录在系统日志中

### ✅ 数据完整性
- **数据库无重复**：通过 Tweet ID 唯一约束确保无重复
- **日志无重复**：通过内容去重确保日志无重复
- **since_id 正确**：每次抓取后正确更新 since_id

### ✅ 日志分流
- **推文日志纯净**：只包含真正的推文数据
- **系统事件分流**：用户跳过、限速等事件写入系统日志
- **时区一致性**：所有时间显示使用北京时间

## 重新启用方法

如需重新启用Twitter抓取功能，可以：

### 1. 恢复DAG文件
```bash
# 从备份恢复DAG文件（如果有）
cp backup/fetch_twitter.py dags/fetch_twitter.py
```

### 2. 手动触发测试
```bash
# 测试Twitter抓取功能
python -m scraper.twitter_scraper
```

### 3. 检查配置
```bash
# 检查环境变量
echo $TWITTER_BEARER_TOKEN
echo $TWITTER_USERS
```

## 监控指标

### 可监控指标
- 限速次数
- 跳过用户数
- 每用户抓取推文数
- API 调用成功率
- 平均响应时间

### 日志文件位置
- **推文日志**：`logs/news/twitter/twitter_YYYY-MM-DD.log`
- **用户进度**：`logs/news/twitter/user_progress.json`
- **用户活跃度**：`logs/system/twitter_activity/twitter_activity_YYYY-MM-DD.log`
- **限速事件**：`logs/system/twitter_quota/twitter_quota_YYYY-MM-DD.log`

## 环境变量

```bash
# Twitter API 配置
TWITTER_BEARER_TOKEN=your_bearer_token
TWITTER_USERS=sentdefender,WallStreetApes

# 可选：兼容旧配置
TW_BEARER_TOKEN=your_bearer_token
```

## 性能提升

### 抓取效率
- **单次请求量**：从 10 条提升到 100 条（10倍）
- **分页抓取**：支持连续翻页，每用户最多 500 条
- **增量抓取**：避免重复获取历史数据

### 限速处理
- **智能跳过**：限速时立即切换用户，不等待
- **最大化覆盖面**：确保在有限配额内覆盖更多用户
- **详细记录**：记录限速事件，便于监控和调试

### 数据质量
- **去重机制**：数据库级和日志级双重去重
- **进度管理**：持久化用户抓取进度
- **错误处理**：完善的异常处理和重试机制

### 日志管理
- **智能分流**：推文和系统事件分别存储
- **时区处理**：统一使用北京时间
- **日志去重**：避免重复日志记录

## 向后兼容

- **数据库结构**：不影响现有数据库表结构
- **调度频率**：保持每小时触发
- **日志格式**：保持现有日志格式，新增字段可选
- **环境变量**：支持新旧环境变量格式

## 故障排除

### 常见问题

#### 1. 限速频繁
- **症状**：大量用户被跳过
- **解决方案**：检查 API 配额，考虑分批抓取或错峰调度

#### 2. 日志文件过大
- **症状**：推文日志包含系统事件
- **解决方案**：检查日志分流配置，确保系统事件写入正确目录

#### 3. 时区显示错误
- **症状**：日志时间显示 UTC 而非北京时间
- **解决方案**：检查时区配置，确保使用 `ZoneInfo('Asia/Shanghai')`

### 调试命令

```bash
# 查看推文日志
tail -f logs/news/twitter/twitter_$(date +%Y-%m-%d).log

# 查看用户活跃度日志
tail -f logs/system/twitter_activity/twitter_activity_$(date +%Y-%m-%d).log

# 查看限速事件日志
tail -f logs/system/twitter_quota/twitter_quota_$(date +%Y-%m-%d).log

# 检查用户进度
cat logs/news/twitter/user_progress.json
``` 