# 文件路径: config/settings.py

# 1. 信源白名单（已迁移至 Airflow Variable: TRUSTED_SOURCES_WHITELIST）
# 这些参数现在通过 Airflow UI 动态管理：
# - TRUSTED_SOURCES_WHITELIST: 可信信源列表（JSON 格式）
# - ENABLE_SOURCE_WHITELIST: 是否启用信源白名单过滤

# TRUSTED_SOURCES = [
#     "tass.ru", "themoscowtimes.com", "ria.ru", "sputniknews.cn",
#     "kyivpost.com", "timesofisrael.com", "bbc.com", "thetimes.co.uk",
#     "nhk.or.jp", "nytimes.com", "cnn.com", "zaobao.com.sg", "reuters.com",
#     "apnews.com", "bloomberg.com", "theguardian.com", "ft.com",
#     "skynews.com", "elpais.com", "scmp.com", "aljazeera.com", "theverge.com"
# ]

# 2. API消耗控制参数 (已迁移至 Airflow Variables)
# 这些参数现在通过 Airflow UI 动态管理：
# - ainews_max_events_to_fetch: 每次运行最多获取的事件数量
# - ainews_articles_per_event: 每个事件最多获取的文章数量

# MAX_EVENTS_TO_FETCH = 50  # 已迁移至 Airflow Variable: ainews_max_events_to_fetch
# ARTICLES_PER_EVENT = 1    # 已迁移至 Airflow Variable: ainews_articles_per_event 