-- 创建每日选题卡片表
CREATE TABLE IF NOT EXISTS daily_cards (
    id BIGSERIAL PRIMARY KEY,
    card_date DATE NOT NULL,
    hashtags TEXT[] NOT NULL,
    title VARCHAR(50) NOT NULL,
    subtitle VARCHAR(100) NOT NULL,
    summary TEXT NOT NULL,
    date VARCHAR(20) NOT NULL,
    source TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_daily_cards_date ON daily_cards(card_date);
CREATE INDEX IF NOT EXISTS idx_daily_cards_created_at ON daily_cards(created_at);

-- 添加注释
COMMENT ON TABLE daily_cards IS '每日选题卡片表';
COMMENT ON COLUMN daily_cards.card_date IS '卡片日期';
COMMENT ON COLUMN daily_cards.hashtags IS '标签数组';
COMMENT ON COLUMN daily_cards.title IS '主标题（≤8字）';
COMMENT ON COLUMN daily_cards.subtitle IS '副标题（≤12字）';
COMMENT ON COLUMN daily_cards.summary IS '摘要（≤200字）';
COMMENT ON COLUMN daily_cards.date IS '报道日期';
COMMENT ON COLUMN daily_cards.source IS '来源信息';
COMMENT ON COLUMN daily_cards.created_at IS '创建时间'; 