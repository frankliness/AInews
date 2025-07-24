-- 去同质化v2数据库迁移
-- 添加EventRegistry相关字段和聚类字段

ALTER TABLE raw_events
  ADD COLUMN IF NOT EXISTS topic_id            BIGINT,
  ADD COLUMN IF NOT EXISTS cluster_size        INT,
  ADD COLUMN IF NOT EXISTS centroid_sim        NUMERIC,
  ADD COLUMN IF NOT EXISTS total_articles_24h  INT,
  ADD COLUMN IF NOT EXISTS source_importance   INT,
  ADD COLUMN IF NOT EXISTS wgt                 INT,
  ADD COLUMN IF NOT EXISTS likes               INT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS retweets            INT DEFAULT 0;

-- 创建索引
CREATE INDEX IF NOT EXISTS ix_raw_events_topic_id ON raw_events(topic_id);
CREATE INDEX IF NOT EXISTS ix_raw_events_published_at ON raw_events(published_at);

-- 添加EventRegistry相关字段
ALTER TABLE raw_events
  ADD COLUMN IF NOT EXISTS event_id            VARCHAR(64),
  ADD COLUMN IF NOT EXISTS embedding           TEXT; -- JSON格式存储向量

-- 创建索引
CREATE INDEX IF NOT EXISTS ix_raw_events_event_id ON raw_events(event_id); 