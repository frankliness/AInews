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

### 3. 配置验证

在 Airflow UI 中验证以下变量是否正确配置：

| 变量名 | 描述 | 默认值 | 验证状态 |
|--------|------|--------|----------|
| `ainews_routine_topic_uris` | 常规话题URI列表 | `[]` | ⚠️ 需要配置 |
| `ainews_downweight_category_uris` | 领域话题URI列表 | `[]` | ⚠️ 需要配置 |
| `ainews_routine_topic_damping_factor` | 抑制强度 | `0.3` | ✅ 默认值 |
| `ainews_category_damping_factor` | 降权强度 | `0.5` | ✅ 默认值 |
| `ainews_freshness_threshold_for_breaking` | 爆点阈值 | `0.8` | ✅ 默认值 |

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

## 🎯 验证清单

### 部署前检查
- [ ] 监控字段已添加到数据库
- [ ] 抑制逻辑已集成到打分流程
- [ ] Airflow Variables已正确配置

### 部署后验证
- [ ] 监控字段存在且可查询
- [ ] 抑制逻辑在日志中正常执行
- [ ] 抑制效果统计数据合理
- [ ] 高分文章排名符合预期

## 总结

通过以上系统性的验证方法，可以确保双重话题抑制功能在生产环境中正确生效。建议定期运行验证脚本，监控抑制效果，并根据实际数据表现调整配置参数。 