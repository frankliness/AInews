-- 添加双重话题抑制监控字段
-- 为 raw_events 表添加抑制功能所需的监控字段

-- 添加监控字段
ALTER TABLE raw_events 
ADD COLUMN IF NOT EXISTS is_routine_topic BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS is_category_topic BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS is_breaking_news BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS is_suppressed BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS is_downweighted BOOLEAN DEFAULT FALSE;

-- 添加字段注释
COMMENT ON COLUMN raw_events.is_routine_topic IS '是否属于常规话题';
COMMENT ON COLUMN raw_events.is_category_topic IS '是否属于领域话题';
COMMENT ON COLUMN raw_events.is_breaking_news IS '是否为爆点新闻';
COMMENT ON COLUMN raw_events.is_suppressed IS '是否被抑制';
COMMENT ON COLUMN raw_events.is_downweighted IS '是否被降权';

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_raw_events_is_routine_topic ON raw_events(is_routine_topic);
CREATE INDEX IF NOT EXISTS idx_raw_events_is_category_topic ON raw_events(is_category_topic);
CREATE INDEX IF NOT EXISTS idx_raw_events_is_breaking_news ON raw_events(is_breaking_news);
CREATE INDEX IF NOT EXISTS idx_raw_events_is_suppressed ON raw_events(is_suppressed);
CREATE INDEX IF NOT EXISTS idx_raw_events_is_downweighted ON raw_events(is_downweighted);

-- 验证字段添加成功
SELECT 
    column_name, 
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'raw_events' 
  AND column_name IN ('is_routine_topic', 'is_category_topic', 'is_breaking_news', 'is_suppressed', 'is_downweighted')
ORDER BY column_name; 