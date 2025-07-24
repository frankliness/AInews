CREATE TABLE IF NOT EXISTS raw_events (
    id            BIGSERIAL PRIMARY KEY,
    source        VARCHAR(32),
    title         TEXT,
    body          TEXT,
    published_at  TIMESTAMPTZ,
    url           TEXT UNIQUE,
    likes         INT,
    retweets      INT,
    collected_at  TIMESTAMPTZ DEFAULT now()
);

