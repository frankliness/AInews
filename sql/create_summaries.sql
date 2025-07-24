-- 汇总表：一条 raw_events 对应一条摘要
CREATE TABLE IF NOT EXISTS summaries (
    id          BIGSERIAL PRIMARY KEY,
    raw_id      BIGINT UNIQUE
                REFERENCES raw_events(id) ON DELETE CASCADE,
    summary_cn  TEXT          NOT NULL,
    summary_en  TEXT          NOT NULL,
    created_at  TIMESTAMPTZ   DEFAULT now()
);
