-- Twitter 用户ID缓存表
-- 用于持久化用户ID，避免重复调用 /users/by/username API

CREATE TABLE IF NOT EXISTS twitter_users (
    id BIGINT NOT NULL,
    username TEXT PRIMARY KEY,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_twitter_users_updated_at ON twitter_users(updated_at);

-- 添加注释
COMMENT ON TABLE twitter_users IS 'Twitter用户ID缓存表，避免重复调用API获取用户ID';
COMMENT ON COLUMN twitter_users.id IS 'Twitter用户ID';
COMMENT ON COLUMN twitter_users.username IS 'Twitter用户名（唯一标识）';
COMMENT ON COLUMN twitter_users.updated_at IS '最后更新时间';
COMMENT ON COLUMN twitter_users.created_at IS '创建时间'; 