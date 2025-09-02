# Phoenix 数据库管理指南

本文档提供 Phoenix 新闻系统的数据库访问和管理信息。

## 🗄️ 数据库管理界面

### pgAdmin 访问信息
- **URL**: http://localhost:5051
- **邮箱**: phoenix@example.com
- **密码**: phoenix123

### 数据库连接参数
- **主机**: postgres-phoenix
- **端口**: 5432
- **数据库**: phoenix_db
- **用户名**: phoenix_user
- **密码**: phoenix_pass

## 🔍 常用数据库操作

### 查看最新新闻数据
```bash
docker compose -f docker-compose.phoenix.yml exec postgres-phoenix \
  psql -U phoenix_user -d phoenix_db \
  -c "SELECT id, left(title,50) AS title_snippet, published_at, final_score_v2
      FROM raw_events 
      WHERE final_score_v2 IS NOT NULL
      ORDER BY final_score_v2 DESC 
      LIMIT 5;"
```

### 查看话题抑制效果
```bash
docker compose -f docker-compose.phoenix.yml exec postgres-phoenix \
  psql -U phoenix_user -d phoenix_db \
  -c "SELECT 
        COUNT(*) as total_articles,
        COUNT(CASE WHEN is_suppressed THEN 1 END) as suppressed_count,
        COUNT(CASE WHEN is_downweighted THEN 1 END) as downweighted_count,
        ROUND(COUNT(CASE WHEN is_suppressed THEN 1 END) * 100.0 / COUNT(*), 2) as suppression_rate
      FROM raw_events 
      WHERE published_at >= NOW() - INTERVAL '24 HOURS';"
```

### 查看概念热度数据
```bash
docker compose -f docker-compose.phoenix.yml exec postgres-phoenix \
  psql -U phoenix_user -d phoenix_db \
  -c "SELECT uri, score, updated_at 
      FROM trending_concepts 
      ORDER BY score DESC 
      LIMIT 10;"
```

## 🛠️ 故障排除

### 检查服务状态
```bash
# 查看所有容器状态
docker compose -f docker-compose.phoenix.yml ps

# 检查数据库连接
docker compose -f docker-compose.phoenix.yml exec postgres-phoenix \
  psql -U phoenix_user -d phoenix_db -c "SELECT version();"
```

### 重启服务
```bash
# 重启 pgAdmin
docker compose -f docker-compose.phoenix.yml restart pgadmin-phoenix

# 重启数据库
docker compose -f docker-compose.phoenix.yml restart postgres-phoenix
```

### 查看日志
```bash
# 查看 pgAdmin 日志
docker compose -f docker-compose.phoenix.yml logs pgadmin-phoenix

# 查看数据库日志
docker compose -f docker-compose.phoenix.yml logs postgres-phoenix
```

## 📊 数据表结构

### raw_events 表（新闻事件主表）
- **id**: 文章唯一标识
- **title**: 文章标题
- **body**: 文章内容
- **published_at**: 发布时间
- **final_score_v2**: 综合评分
- **is_suppressed**: 是否被抑制
- **is_downweighted**: 是否被降权

### trending_concepts 表（概念热度表）
- **uri**: 概念URI
- **score**: 热度分数
- **updated_at**: 更新时间

---

*最后更新: 2025年9月2日* 