# 生产环境双重话题抑制功能验证指南

## 概述

本文档提供了在生产环境中验证双重话题抑制功能是否生效的完整方案。

## 🔍 验证方法

### 1. 实时监控验证

#### 查看Airflow日志
```bash
# 查看最新的打分任务日志
docker-compose -f docker-compose.phoenix.yml logs phoenix-webserver | grep "Topic suppression"
```

#### 检查抑制效果日志
在Airflow UI中查看DAG执行日志，寻找以下关键信息：
- `"Applying dual topic suppression & down-weighting logic using vectorized operations..."`
- `"Suppressed X routine articles and down-weighted Y category articles."`
- `"Topic suppression and down-weighting logic applied."`

### 2. 数据库查询验证

#### 检查监控字段是否存在
```sql
-- 验证新增的监控字段是否已添加到数据库
SELECT 
    column_name, 
    data_type 
FROM information_schema.columns 
WHERE table_name = 'raw_events' 
  AND column_name IN ('is_routine_topic', 'is_category_topic', 'is_breaking_news', 'is_suppressed', 'is_downweighted');
```

#### 实时抑制效果统计
```sql
-- 查看最近24小时的抑制效果
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
```

### 3. 自动化验证脚本

#### 运行验证脚本
```bash
# 复制验证脚本到容器
docker cp scripts/verify_production_suppression.py dev-phoenix-webserver-1:/opt/airflow/

# 运行验证脚本
docker-compose -f docker-compose.phoenix.yml exec phoenix-webserver python /opt/airflow/verify_production_suppression.py
```

#### 验证脚本输出解读
- ✅ **监控字段验证**: 确认5个监控字段已存在
- 📊 **抑制效果统计**: 查看被抑制和降权的文章数量
- 📈 **话题分布分析**: 了解不同类型话题的分布
- 🏆 **高分文章分析**: 检查抑制对排名的影响
- ⚙️ **配置验证**: 确认Airflow Variables设置

### 4. 配置验证

#### 检查Airflow Variables
在Airflow UI中验证以下变量是否正确配置：

| 变量名 | 描述 | 默认值 | 验证状态 |
|--------|------|--------|----------|
| `ainews_routine_topic_uris` | 常规话题URI列表 | `[]` | ⚠️ 需要配置 |
| `ainews_downweight_category_uris` | 领域话题URI列表 | `[]` | ⚠️ 需要配置 |
| `ainews_routine_topic_damping_factor` | 抑制强度 | `0.3` | ✅ 默认值 |
| `ainews_category_damping_factor` | 降权强度 | `0.5` | ✅ 默认值 |
| `ainews_freshness_threshold_for_breaking` | 爆点阈值 | `0.8` | ✅ 默认值 |

#### 配置示例
```json
// ainews_routine_topic_uris
[
  "http://en.wikipedia.org/wiki/Gaza_Strip",
  "http://en.wikipedia.org/wiki/Israel–Hamas_war",
  "http://en.wikipedia.org/wiki/Russo-Ukrainian_War",
  "http://en.wikipedia.org/wiki/Russian_invasion_of_Ukraine"
]

// ainews_downweight_category_uris
[
  "http://en.wikipedia.org/wiki/Arts",
  "http://en.wikipedia.org/wiki/Culture",
  "http://en.wikipedia.org/wiki/Entertainment",
  "http://en.wikipedia.org/wiki/Sport"
]
```

### 5. 对比分析验证

#### 抑制前后分数对比
```sql
-- 分析被抑制文章的分数变化
SELECT 
    title,
    source_name,
    published_at,
    hot_norm,
    final_score_v2,
    is_routine_topic,
    is_breaking_news,
    is_suppressed,
    is_downweighted
FROM raw_events 
WHERE published_at >= NOW() - INTERVAL '24 HOURS'
  AND (is_suppressed = true OR is_downweighted = true)
ORDER BY published_at DESC
LIMIT 20;
```

#### 话题类型分布分析
```sql
-- 查看不同类型话题的分布和分数
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
```

### 6. 性能监控验证

#### 检查处理时间
```sql
-- 监控打分任务的执行时间
SELECT 
    dag_id,
    task_id,
    start_date,
    end_date,
    EXTRACT(EPOCH FROM (end_date - start_date)) as duration_seconds
FROM task_instance 
WHERE dag_id LIKE '%scorer%' 
  AND start_date >= NOW() - INTERVAL '24 HOURS'
ORDER BY start_date DESC;
```

## 📊 验证指标

### 成功指标
- ✅ 监控字段已添加到数据库
- ✅ 抑制逻辑在日志中正常执行
- ✅ 被抑制和降权的文章数量 > 0
- ✅ 高分文章排名合理
- ✅ 配置参数正确设置

### 警告指标
- ⚠️ 抑制率为0% - 可能需要配置话题URI列表
- ⚠️ 降权率为0% - 可能需要配置领域话题列表
- ⚠️ 处理时间异常 - 可能需要性能优化

### 失败指标
- ❌ 监控字段缺失
- ❌ 抑制逻辑未执行
- ❌ 配置参数错误
- ❌ 数据库连接失败

## 🔧 故障排查

### 常见问题及解决方案

#### 1. 监控字段不存在
```sql
-- 添加监控字段
ALTER TABLE raw_events 
ADD COLUMN IF NOT EXISTS is_routine_topic BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS is_category_topic BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS is_breaking_news BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS is_suppressed BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS is_downweighted BOOLEAN DEFAULT FALSE;
```

#### 2. 抑制效果为0
- 检查Airflow Variables中的话题URI列表是否配置
- 确认文章的概念(concepts)字段包含相关URI
- 验证新鲜度阈值设置是否合理

#### 3. 性能问题
- 检查数据库索引是否创建
- 监控内存使用情况
- 优化查询性能

## 📈 持续监控

### 日常监控查询
```sql
-- 每日抑制效果报告
SELECT 
    DATE(published_at) as date,
    COUNT(*) as total_articles,
    COUNT(CASE WHEN is_suppressed = true THEN 1 END) as suppressed_count,
    COUNT(CASE WHEN is_downweighted = true THEN 1 END) as downweighted_count,
    ROUND(COUNT(CASE WHEN is_suppressed = true THEN 1 END) * 100.0 / COUNT(*), 2) as suppression_rate
FROM raw_events 
WHERE published_at >= NOW() - INTERVAL '7 DAYS'
GROUP BY DATE(published_at)
ORDER BY date DESC;
```

### 趋势分析
```sql
-- 抑制效果趋势分析
SELECT 
    EXTRACT(HOUR FROM published_at) as hour,
    COUNT(*) as total_articles,
    COUNT(CASE WHEN is_suppressed = true THEN 1 END) as suppressed_count,
    ROUND(COUNT(CASE WHEN is_suppressed = true THEN 1 END) * 100.0 / COUNT(*), 2) as suppression_rate
FROM raw_events 
WHERE published_at >= NOW() - INTERVAL '24 HOURS'
GROUP BY hour
ORDER BY hour;
```

## 🎯 验证清单

### 部署前检查
- [ ] 监控字段已添加到数据库
- [ ] 抑制逻辑已集成到打分流程
- [ ] Airflow Variables已正确配置
- [ ] 测试脚本已验证功能

### 部署后验证
- [ ] 监控字段存在且可查询
- [ ] 抑制逻辑在日志中正常执行
- [ ] 抑制效果统计数据合理
- [ ] 高分文章排名符合预期
- [ ] 性能指标正常

### 持续监控
- [ ] 每日抑制效果报告
- [ ] 话题分布趋势分析
- [ ] 性能监控指标
- [ ] 配置参数定期检查

## 总结

通过以上系统性的验证方法，可以确保双重话题抑制功能在生产环境中正确生效。建议定期运行验证脚本，监控抑制效果，并根据实际数据表现调整配置参数。 