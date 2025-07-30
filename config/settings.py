# 文件路径: config/settings.py

# 1. 信源白名单
# 我们只采纳这些主流、可靠媒体发布的新闻



TRUSTED_SOURCES = [
    "tass.ru", "themoscowtimes.com", "ria.ru", "sputniknews.cn",
    "kyivpost.com", "timesofisrael.com", "bbc.com", "thetimes.co.uk",
    "nhk.or.jp", "nytimes.com", "cnn.com", "zaobao.com.sg", "reuters.com",
    "apnews.com", "bloomberg.com", "theguardian.com", "ft.com",
    "skynews.com", "elpais.com", "scmp.com", "aljazeera.com", "theverge.com"
]

# 2. API消耗控制参数 (可配置)
# 在测试时可以调低这些值，在生产环境中调高

MAX_EVENTS_TO_FETCH = 10  # 每次运行最多获取的事件数量
ARTICLES_PER_EVENT = 2     # 每个事件最多获取的文章数量 