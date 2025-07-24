-- 去同质化v2系统监控查询
-- 用于监控聚类效果、打分分布、系统性能等关键指标

-- ===========================================
-- 1. 聚类效果监控
-- ===========================================

-- 1.1 基础聚类统计
SELECT 
    COUNT(DISTINCT topic_id) as unique_topics,
    AVG(cluster_size) as avg_cluster_size,
    MAX(cluster_size) as max_cluster_size,
    MIN(cluster_size) as min_cluster_size,
    COUNT(*) as total_articles
FROM raw_events 
WHERE topic_id IS NOT NULL 
  AND published_at >= NOW() - INTERVAL '24 HOURS';

-- 1.2 聚类大小分布
SELECT 
    cluster_size,
    COUNT(*) as topic_count
FROM (
    SELECT topic_id, COUNT(*) as cluster_size
    FROM raw_events 
    WHERE topic_id IS NOT NULL 
      AND published_at >= NOW() - INTERVAL '24 HOURS'
    GROUP BY topic_id
) t
GROUP BY cluster_size
ORDER BY cluster_size;

-- 1.3 聚类中心相似度分布
SELECT 
    CASE 
        WHEN centroid_sim IS NULL THEN 'NULL'
        WHEN centroid_sim < 0.3 THEN 'LOW (<0.3)'
        WHEN centroid_sim < 0.7 THEN 'MEDIUM (0.3-0.7)'
        ELSE 'HIGH (>0.7)'
    END as similarity_level,
    COUNT(*) as article_count
FROM raw_events 
WHERE topic_id IS NOT NULL 
  AND published_at >= NOW() - INTERVAL '24 HOURS'
GROUP BY similarity_level
ORDER BY similarity_level;

-- ===========================================
-- 2. 打分分布监控
-- ===========================================

-- 2.1 基础打分统计
SELECT 
    COUNT(*) as total_records,
    COUNT(CASE WHEN score IS NOT NULL THEN 1 END) as scored_records,
    COUNT(CASE WHEN score >= 0.6 THEN 1 END) as high_score_records,
    COUNT(CASE WHEN score >= 0.8 THEN 1 END) as very_high_score_records,
    AVG(score) as avg_score,
    MIN(score) as min_score,
    MAX(score) as max_score,
    STDDEV(score) as score_stddev
FROM raw_events 
WHERE score IS NOT NULL 
  AND published_at >= NOW() - INTERVAL '24 HOURS';

-- 2.2 打分分布直方图
SELECT 
    CASE 
        WHEN score < 0.1 THEN '0.0-0.1'
        WHEN score < 0.2 THEN '0.1-0.2'
        WHEN score < 0.3 THEN '0.2-0.3'
        WHEN score < 0.4 THEN '0.3-0.4'
        WHEN score < 0.5 THEN '0.4-0.5'
        WHEN score < 0.6 THEN '0.5-0.6'
        WHEN score < 0.7 THEN '0.6-0.7'
        WHEN score < 0.8 THEN '0.7-0.8'
        WHEN score < 0.9 THEN '0.8-0.9'
        ELSE '0.9-1.0'
    END as score_range,
    COUNT(*) as article_count
FROM raw_events 
WHERE score IS NOT NULL 
  AND published_at >= NOW() - INTERVAL '24 HOURS'
GROUP BY score_range
ORDER BY score_range;

-- 2.3 各维度分数分析
SELECT 
    AVG(hot_raw) as avg_hot_raw,
    AVG(hot_norm) as avg_hot_norm,
    AVG(rep_norm) as avg_rep_norm,
    AVG(sent_norm) as avg_sent_norm,
    AVG(score) as avg_total_score
FROM raw_events 
WHERE score IS NOT NULL 
  AND published_at >= NOW() - INTERVAL '24 HOURS';

-- ===========================================
-- 3. EventRegistry字段监控
-- ===========================================

-- 3.1 EventRegistry字段完整性
SELECT 
    COUNT(*) as total_records,
    COUNT(CASE WHEN event_id IS NOT NULL THEN 1 END) as has_event_id,
    COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as has_embedding,
    COUNT(CASE WHEN total_articles_24h IS NOT NULL THEN 1 END) as has_total_articles,
    COUNT(CASE WHEN source_importance IS NOT NULL THEN 1 END) as has_source_importance,
    COUNT(CASE WHEN wgt IS NOT NULL THEN 1 END) as has_wgt
FROM raw_events 
WHERE published_at >= NOW() - INTERVAL '24 HOURS';

-- 3.2 EventRegistry字段分布
SELECT 
    'total_articles_24h' as field_name,
    MIN(total_articles_24h) as min_value,
    MAX(total_articles_24h) as max_value,
    AVG(total_articles_24h) as avg_value,
    COUNT(*) as record_count
FROM raw_events 
WHERE total_articles_24h IS NOT NULL 
  AND published_at >= NOW() - INTERVAL '24 HOURS'

UNION ALL

SELECT 
    'source_importance' as field_name,
    MIN(source_importance) as min_value,
    MAX(source_importance) as max_value,
    AVG(source_importance) as avg_value,
    COUNT(*) as record_count
FROM raw_events 
WHERE source_importance IS NOT NULL 
  AND published_at >= NOW() - INTERVAL '24 HOURS'

UNION ALL

SELECT 
    'wgt' as field_name,
    MIN(wgt) as min_value,
    MAX(wgt) as max_value,
    AVG(wgt) as avg_value,
    COUNT(*) as record_count
FROM raw_events 
WHERE wgt IS NOT NULL 
  AND published_at >= NOW() - INTERVAL '24 HOURS';

-- ===========================================
-- 4. 数据源分析
-- ===========================================

-- 4.1 各数据源统计
SELECT 
    source,
    COUNT(*) as article_count,
    COUNT(CASE WHEN event_id IS NOT NULL THEN 1 END) as eventregistry_articles,
    AVG(score) as avg_score,
    MAX(score) as max_score
FROM raw_events 
WHERE published_at >= NOW() - INTERVAL '24 HOURS'
GROUP BY source
ORDER BY article_count DESC;

-- 4.2 数据源质量分析
SELECT 
    source,
    COUNT(*) as total_articles,
    COUNT(CASE WHEN topic_id IS NOT NULL THEN 1 END) as clustered_articles,
    COUNT(CASE WHEN score IS NOT NULL THEN 1 END) as scored_articles,
    ROUND(COUNT(CASE WHEN topic_id IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as clustering_rate,
    ROUND(COUNT(CASE WHEN score IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as scoring_rate
FROM raw_events 
WHERE published_at >= NOW() - INTERVAL '24 HOURS'
GROUP BY source
ORDER BY total_articles DESC;

-- ===========================================
-- 5. 时间分布分析
-- ===========================================

-- 5.1 每小时数据分布
SELECT 
    EXTRACT(HOUR FROM published_at) as hour,
    COUNT(*) as article_count,
    AVG(score) as avg_score
FROM raw_events 
WHERE published_at >= NOW() - INTERVAL '24 HOURS'
GROUP BY hour
ORDER BY hour;

-- 5.2 数据新鲜度分析
SELECT 
    CASE 
        WHEN published_at >= NOW() - INTERVAL '1 HOUR' THEN '1小时内'
        WHEN published_at >= NOW() - INTERVAL '6 HOUR' THEN '1-6小时'
        WHEN published_at >= NOW() - INTERVAL '12 HOUR' THEN '6-12小时'
        WHEN published_at >= NOW() - INTERVAL '24 HOUR' THEN '12-24小时'
        ELSE '超过24小时'
    END as time_range,
    COUNT(*) as article_count,
    AVG(score) as avg_score
FROM raw_events 
WHERE published_at >= NOW() - INTERVAL '24 HOURS'
GROUP BY time_range
ORDER BY time_range;

-- ===========================================
-- 6. 情感分析监控
-- ===========================================

-- 6.1 情感分布
SELECT 
    CASE 
        WHEN sentiment < -0.3 THEN '负面'
        WHEN sentiment > 0.3 THEN '正面'
        ELSE '中性'
    END as sentiment_category,
    COUNT(*) as article_count,
    AVG(score) as avg_score
FROM raw_events 
WHERE sentiment IS NOT NULL 
  AND published_at >= NOW() - INTERVAL '24 HOURS'
GROUP BY sentiment_category
ORDER BY sentiment_category;

-- 6.2 情感分数分布
SELECT 
    CASE 
        WHEN sentiment < -0.8 THEN '极负面'
        WHEN sentiment < -0.3 THEN '负面'
        WHEN sentiment < 0.3 THEN '中性'
        WHEN sentiment < 0.8 THEN '正面'
        ELSE '极正面'
    END as sentiment_level,
    COUNT(*) as article_count
FROM raw_events 
WHERE sentiment IS NOT NULL 
  AND published_at >= NOW() - INTERVAL '24 HOURS'
GROUP BY sentiment_level
ORDER BY sentiment_level;

-- ===========================================
-- 7. 系统性能监控
-- ===========================================

-- 7.1 数据库表大小
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats 
WHERE tablename = 'raw_events'
ORDER BY attname;

-- 7.2 索引使用情况
SELECT 
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes 
WHERE tablename = 'raw_events'
ORDER BY idx_scan DESC;

-- ===========================================
-- 8. 质量评估查询
-- ===========================================

-- 8.1 高分新闻分析
SELECT 
    title,
    source,
    published_at,
    score,
    hot_norm,
    rep_norm,
    sent_norm,
    topic_id,
    cluster_size
FROM raw_events 
WHERE score >= 0.6 
  AND published_at >= NOW() - INTERVAL '24 HOURS'
ORDER BY score DESC
LIMIT 20;

-- 8.2 聚类质量评估
SELECT 
    topic_id,
    COUNT(*) as cluster_size,
    AVG(score) as avg_score,
    MAX(score) as max_score,
    MIN(score) as min_score,
    AVG(centroid_sim) as avg_similarity
FROM raw_events 
WHERE topic_id IS NOT NULL 
  AND published_at >= NOW() - INTERVAL '24 HOURS'
GROUP BY topic_id
ORDER BY cluster_size DESC, avg_score DESC
LIMIT 20;

-- 8.3 数据完整性检查
SELECT 
    'Missing event_id' as issue,
    COUNT(*) as count
FROM raw_events 
WHERE event_id IS NULL 
  AND published_at >= NOW() - INTERVAL '24 HOURS'

UNION ALL

SELECT 
    'Missing embedding' as issue,
    COUNT(*) as count
FROM raw_events 
WHERE embedding IS NULL 
  AND published_at >= NOW() - INTERVAL '24 HOURS'

UNION ALL

SELECT 
    'Missing sentiment' as issue,
    COUNT(*) as count
FROM raw_events 
WHERE sentiment IS NULL 
  AND published_at >= NOW() - INTERVAL '24 HOURS'

UNION ALL

SELECT 
    'Missing score' as issue,
    COUNT(*) as count
FROM raw_events 
WHERE score IS NULL 
  AND published_at >= NOW() - INTERVAL '24 HOURS';

-- ===========================================
-- 9. 实时监控仪表板查询
-- ===========================================

-- 9.1 系统概览
SELECT 
    (SELECT COUNT(*) FROM raw_events WHERE published_at >= NOW() - INTERVAL '24 HOURS') as total_articles_24h,
    (SELECT COUNT(DISTINCT topic_id) FROM raw_events WHERE topic_id IS NOT NULL AND published_at >= NOW() - INTERVAL '24 HOURS') as unique_topics,
    (SELECT COUNT(*) FROM raw_events WHERE score >= 0.6 AND published_at >= NOW() - INTERVAL '24 HOURS') as high_score_articles,
    (SELECT AVG(score) FROM raw_events WHERE score IS NOT NULL AND published_at >= NOW() - INTERVAL '24 HOURS') as avg_score,
    (SELECT COUNT(DISTINCT source) FROM raw_events WHERE published_at >= NOW() - INTERVAL '24 HOURS') as active_sources;

-- 9.2 最近1小时活动
SELECT 
    COUNT(*) as articles_last_hour,
    COUNT(DISTINCT source) as sources_last_hour,
    AVG(score) as avg_score_last_hour
FROM raw_events 
WHERE published_at >= NOW() - INTERVAL '1 HOUR';

-- 9.3 系统健康状态
SELECT 
    CASE 
        WHEN (SELECT COUNT(*) FROM raw_events WHERE published_at >= NOW() - INTERVAL '1 HOUR') > 0 THEN '正常'
        ELSE '异常'
    END as data_collection_status,
    CASE 
        WHEN (SELECT COUNT(*) FROM raw_events WHERE score IS NOT NULL AND published_at >= NOW() - INTERVAL '1 HOUR') > 0 THEN '正常'
        ELSE '异常'
    END as scoring_status,
    CASE 
        WHEN (SELECT COUNT(*) FROM raw_events WHERE topic_id IS NOT NULL AND published_at >= NOW() - INTERVAL '1 HOUR') > 0 THEN '正常'
        ELSE '异常'
    END as clustering_status; 