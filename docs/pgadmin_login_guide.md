# pgAdmin 登录指南

本文档记录了系统中所有pgAdmin实例的登录信息，方便快速访问数据库管理界面。

## V1 系统 (旧版本)

### pgAdmin 访问信息
- **URL**: http://localhost:5050
- **邮箱**: 从环境变量读取 (PGADMIN_DEFAULT_EMAIL)
- **密码**: 从环境变量读取 (PGADMIN_DEFAULT_PASSWORD)

### 数据库连接参数
- **主机**: host.docker.internal
- **端口**: 5432
- **数据库**: ainews
- **用户名**: airflow
- **密码**: airflow_pass

---

## Phoenix V2 系统 (新版本)

### pgAdmin 访问信息
- **URL**: http://localhost:5051
- **邮箱**: phoenix@example.com
- **密码**: phoenix123

### 数据库连接参数
- **主机**: host.docker.internal
- **端口**: 5434
- **数据库**: phoenix_db
- **用户名**: phoenix_user
- **密码**: phoenix_pass

---

## 常用数据库操作命令

### 查看最新数据
```bash
# V1 系统
docker compose exec postgres \
  psql -U airflow -d ainews \
  -c "SELECT id, source, left(title,50) AS title_snip, published_at
      FROM raw_events
      ORDER BY id DESC
      LIMIT 3;"

# V2 系统
docker compose exec postgres-phoenix \
  psql -U phoenix_user -d phoenix_db \
  -c "SELECT id, source, left(title,50) AS title_snip, published_at
      FROM raw_events
      ORDER BY id DESC
      LIMIT 3;"
```

### 查看摘要统计
```bash
# V1 系统
docker compose exec postgres \
  psql -U airflow -d ainews \
  -c "SELECT COUNT(*) FROM summaries;"

# V2 系统
docker compose exec postgres-phoenix \
  psql -U phoenix_user -d phoenix_db \
  -c "SELECT COUNT(*) FROM summaries;"
```

### 清空摘要表（重新处理所有事件）
```bash
# V1 系统
docker compose exec postgres \
  psql -U airflow -d ainews \
  -c "TRUNCATE TABLE summaries RESTART IDENTITY;"

# V2 系统
docker compose exec postgres-phoenix \
  psql -U phoenix_user -d phoenix_db \
  -c "TRUNCATE TABLE summaries RESTART IDENTITY;"
```

---

## 故障排除

### 如果无法访问pgAdmin
1. 检查Docker容器是否运行：
   ```bash
   docker compose ps
   ```

2. 重启pgAdmin服务：
   ```bash
   # V1 系统
   docker compose restart pgadmin
   
   # V2 系统
   docker compose -f docker-compose.phoenix.yml restart pgadmin-phoenix
   ```

3. 查看pgAdmin日志：
   ```bash
   # V1 系统
   docker compose logs pgadmin
   
   # V2 系统
   docker compose -f docker-compose.phoenix.yml logs pgadmin-phoenix
   ```

### 备份pgAdmin配置
```bash
# 查看卷是否存在
docker volume ls | grep pgadmin-data

# 备份pgAdmin配置
docker run --rm -v pgadmin-data:/data alpine \
  tar -czf - -C /data . > pgadmin_backup_$(date +%F).tgz
```

---

## 注意事项

1. **端口冲突**: V1系统使用端口5050，V2系统使用端口5051，避免冲突
2. **数据库端口**: V1系统使用5432，V2系统使用5434
3. **网络隔离**: 两个系统使用不同的Docker网络，互不影响
4. **数据持久化**: 两个系统的数据分别存储在不同的Docker卷中

---

*最后更新: $(date)* 