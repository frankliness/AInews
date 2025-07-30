-- V2系统建表语句
-- 创建时间: 2024年
-- 描述: V2系统基础设施 - raw_events和trending_concepts表

-- raw_events表 - 存储所有V2新闻事件数据
CREATE TABLE IF NOT EXISTS raw_events (
    id VARCHAR(255) PRIMARY KEY,
    title TEXT,
    body TEXT,
    url TEXT,
    published_at TIMESTAMPTZ,
    collected_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    sentiment NUMERIC,
    source_name VARCHAR(255),
    source_importance INTEGER,
    event_uri VARCHAR(255),
    total_articles_in_event INTEGER,
    concepts JSONB,
    -- V2分数字段
    final_score_v2 NUMERIC,
    hot_norm NUMERIC,
    rep_norm NUMERIC,
    sent_norm NUMERIC,
    entity_hot_score NUMERIC,
    hot_score_v2 NUMERIC,
    rep_score_v2 NUMERIC,
    sent_score_v2 NUMERIC
);

-- trending_concepts表 - 存储概念热度数据
CREATE TABLE IF NOT EXISTS trending_concepts (
    uri VARCHAR(255) PRIMARY KEY,
    score NUMERIC,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
); 