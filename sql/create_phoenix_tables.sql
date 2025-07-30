-- Phoenix V2 专用表结构
-- 在独立数据库实例中创建表

-- 创建原始事件表
CREATE TABLE IF NOT EXISTS raw_events (
    id SERIAL PRIMARY KEY,
    title TEXT,
    body TEXT,
    url TEXT,
    published_at TIMESTAMP WITH TIME ZONE,
    sentiment FLOAT DEFAULT 0.0,
    relevance FLOAT DEFAULT 1.0,
    weight FLOAT DEFAULT 1.0,
    event_uri TEXT,
    source_name TEXT,
    source_importance INTEGER DEFAULT 1,
    total_articles_24h INTEGER DEFAULT 0,
    embedding TEXT,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    source TEXT DEFAULT 'phoenix_v2',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_phoenix_raw_events_published_at ON raw_events(published_at);
CREATE INDEX IF NOT EXISTS idx_phoenix_raw_events_event_uri ON raw_events(event_uri);
CREATE INDEX IF NOT EXISTS idx_phoenix_raw_events_source ON raw_events(source);
CREATE INDEX IF NOT EXISTS idx_phoenix_raw_events_collected_at ON raw_events(collected_at);

-- 创建事件汇总表
CREATE TABLE IF NOT EXISTS event_summaries (
    id SERIAL PRIMARY KEY,
    event_uri TEXT UNIQUE NOT NULL,
    event_title TEXT,
    event_description TEXT,
    article_count INTEGER DEFAULT 0,
    avg_sentiment FLOAT DEFAULT 0.0,
    total_weight FLOAT DEFAULT 0.0,
    top_sources TEXT[],
    concepts TEXT[],
    first_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_phoenix_event_summaries_event_uri ON event_summaries(event_uri);
CREATE INDEX IF NOT EXISTS idx_phoenix_event_summaries_last_updated ON event_summaries(last_updated);

-- 创建数据质量监控表
CREATE TABLE IF NOT EXISTS data_quality_metrics (
    id SERIAL PRIMARY KEY,
    metric_date DATE DEFAULT CURRENT_DATE,
    total_articles INTEGER DEFAULT 0,
    unique_events INTEGER DEFAULT 0,
    avg_sentiment FLOAT DEFAULT 0.0,
    avg_relevance FLOAT DEFAULT 0.0,
    source_diversity INTEGER DEFAULT 0,
    data_completeness FLOAT DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建唯一约束
CREATE UNIQUE INDEX IF NOT EXISTS idx_phoenix_data_quality_metrics_date ON data_quality_metrics(metric_date);

 