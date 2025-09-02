# Phoenix新闻系统 Ubuntu服务器部署指南

## 🎯 系统概述

Phoenix v2.4.1 是一个基于Apache Airflow的智能新闻处理系统，专注于高质量新闻事件的采集、评分和摘要生成。系统通过EventRegistry API实现新闻采集，采用五维度评分算法和双重话题抑制机制，实现新闻内容的智能去重和优先级排序。

### 核心特性
- **智能新闻采集**: 基于EventRegistry API的实时新闻采集，支持多源并行抓取
- **五维度评分系统**: 热度、权威、概念热度、新鲜度、情感五个维度的综合评分
- **双重话题抑制**: 常规话题抑制 + 领域话题降权机制
- **自动化摘要生成**: 每日自动生成JSON格式的新闻摘要
- **API配额管理**: 自动密钥轮换和配额监控

## 📋 系统要求

### 硬件要求
- **CPU**: 至少2核心（推荐4核心）
- **内存**: 至少4GB RAM（推荐8GB）
- **存储**: 至少20GB可用空间（推荐50GB）
- **网络**: 稳定的互联网连接

### 软件要求
- **操作系统**: Ubuntu 20.04 LTS 或更高版本
- **Docker**: 20.10 或更高版本
- **Docker Compose**: 2.0 或更高版本
- **Git**: 用于代码管理

## 🚀 快速部署

### 方法一：使用自动部署脚本（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/frankliness/AInews.git
cd AInews

# 2. 运行自动部署脚本
chmod +x scripts/deploy_to_ubuntu.sh
./scripts/deploy_to_ubuntu.sh
```

### 方法二：手动部署

#### 1. 系统准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础工具
sudo apt install -y curl wget git unzip software-properties-common \
    apt-transport-https ca-certificates gnupg lsb-release
```

#### 2. 安装Docker

```bash
# 添加Docker官方GPG密钥
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# 添加Docker仓库
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 配置Docker用户组
sudo usermod -aG docker $USER
newgrp docker

# 启动Docker服务
sudo systemctl start docker
sudo systemctl enable docker
```

#### 3. 安装Docker Compose

```bash
# 下载Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# 设置执行权限
sudo chmod +x /usr/local/bin/docker-compose

# 验证安装
docker-compose --version
```

#### 4. 部署Phoenix系统

```bash
# 创建项目目录
sudo mkdir -p /opt/phoenix
sudo chown $USER:$USER /opt/phoenix
cd /opt/phoenix

# 克隆项目代码
git clone https://github.com/frankliness/AInews.git .

# 创建必要目录
mkdir -p logs exports
chmod 755 logs exports
```

#### 5. 配置环境变量

```bash
# 创建环境配置文件
cat > .env << 'EOF'
# Phoenix系统环境配置
POSTGRES_USER=phoenix_user
POSTGRES_PASSWORD=phoenix_pass
POSTGRES_DB=phoenix_db
PGADMIN_DEFAULT_EMAIL=phoenix@example.com
PGADMIN_DEFAULT_PASSWORD=phoenix123

# 时区设置
TZ=Asia/Shanghai
PGTZ=Asia/Shanghai
EOF
```

#### 6. 启动Phoenix系统

```bash
# 启动所有服务
docker-compose -f docker-compose.phoenix.yml up -d

# 检查服务状态
docker-compose -f docker-compose.phoenix.yml ps
```

#### 7. 配置防火墙

```bash
# 安装UFW防火墙
sudo apt install -y ufw

# 配置防火墙规则
sudo ufw allow ssh
sudo ufw allow 8082  # Phoenix Airflow Web界面
sudo ufw allow 5051  # Phoenix pgAdmin管理界面
sudo ufw allow 5434  # Phoenix PostgreSQL（可选，用于外部访问）

# 启用防火墙
sudo ufw enable
```

## 🔑 API密钥配置

Phoenix系统使用Airflow Variables来管理API密钥和配置参数。部署完成后，需要通过Airflow Web界面配置以下变量：

### 1. 访问Airflow Web界面

- **URL**: http://your-server-ip:8082
- **用户名**: `phoenix_admin`
- **密码**: `phoenix123`

### 2. 配置EventRegistry API密钥

在Airflow Web界面中，进入 **Admin > Variables**，添加以下变量：

#### 必需变量

| 变量名 | 类型 | 描述 | 示例值 |
|--------|------|------|--------|
| `ainews_eventregistry_apikeys` | JSON | EventRegistry API密钥列表 | `{"keys":["your_api_key_1","your_api_key_2"]}` |

#### 可选配置变量

| 变量名 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| `ENABLE_SOURCE_WHITELIST` | String | `True` | 是否启用信源白名单过滤 |
| `TRUSTED_SOURCES_WHITELIST` | JSON | `[]` | 可信信源列表 |
| `ainews_articles_per_event` | String | `1` | 每个事件获取的文章数量 |
| `ainews_popular_events_limit` | String | `30` | 热门事件数量限制 |
| `ainews_breaking_events_limit` | String | `20` | 突发事件数量限制 |
| `ainews_breaking_recent_hours` | String | `6` | 突发事件时间范围（小时） |

#### 评分权重配置

| 变量名 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| `ainews_weight_hot` | String | `0.35` | 热度分数权重 |
| `ainews_weight_authority` | String | `0.25` | 权威分数权重 |
| `ainews_weight_concept` | String | `0.20` | 概念热度分数权重 |
| `ainews_weight_freshness` | String | `0.15` | 新鲜度分数权重 |
| `ainews_weight_sentiment` | String | `0.05` | 情感分数权重 |

#### 话题抑制配置

| 变量名 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| `ainews_routine_topic_uris` | JSON | `[]` | 常规话题URI列表 |
| `ainews_downweight_category_uris` | JSON | `[]` | 降权分类URI列表 |
| `ainews_routine_topic_damping_factor` | String | `0.3` | 常规话题抑制强度 |
| `ainews_category_damping_factor` | String | `0.5` | 分类降权强度 |
| `ainews_freshness_threshold_for_breaking` | String | `0.8` | 突发新闻新鲜度阈值 |

### 3. 配置示例

```json
// ainews_eventregistry_apikeys
{
  "keys": [
    "your_eventregistry_api_key_1",
    "your_eventregistry_api_key_2"
  ]
}

// TRUSTED_SOURCES_WHITELIST
[
  "Reuters",
  "Associated Press",
  "BBC News",
  "CNN",
  "The New York Times"
]

// ainews_routine_topic_uris
[
  "http://en.wikipedia.org/wiki/Weather",
  "http://en.wikipedia.org/wiki/Sports"
]
```

## 🔍 部署验证

### 1. 检查服务状态

```bash
# 检查所有容器状态
docker-compose -f docker-compose.phoenix.yml ps

# 检查容器日志
docker-compose -f docker-compose.phoenix.yml logs phoenix-webserver
docker-compose -f docker-compose.phoenix.yml logs phoenix-scheduler
```

### 2. 访问Web界面

- **Phoenix Airflow UI**: http://your-server-ip:8082
  - 用户名: `phoenix_admin`
  - 密码: `phoenix123`
- **Phoenix pgAdmin**: http://your-server-ip:5051
  - 用户名: `phoenix@example.com`
  - 密码: `phoenix123`

### 3. 测试系统功能

```bash
# 测试数据库连接
docker-compose -f docker-compose.phoenix.yml exec phoenix-webserver python -c "
from sqlalchemy import create_engine
engine = create_engine('postgresql+psycopg2://phoenix_user:phoenix_pass@postgres-phoenix:5432/phoenix_db')
print('数据库连接成功！')
"

# 检查DAG状态
docker-compose -f docker-compose.phoenix.yml exec phoenix-webserver airflow dags list

# 手动触发DAG测试
docker-compose -f docker-compose.phoenix.yml exec phoenix-webserver \
  airflow dags trigger ingestion_scoring_pipeline
```

### 4. 验证API配置

```bash
# 检查API密钥配置
docker-compose -f docker-compose.phoenix.yml exec phoenix-webserver \
  airflow variables get ainews_eventregistry_apikeys
```

## 📊 系统架构

### Phoenix核心组件

```
Phoenix 新闻处理系统
├── Web 服务 (端口 8082) - Airflow UI
├── 数据库 (端口 5434) - PostgreSQL
├── 管理界面 (端口 5051) - pgAdmin
├── Redis 缓存 (端口 6381)
└── 文件导出目录 (exports/)
```

### 数据处理流程

```
EventRegistry API
    ↓ 新闻采集
ingestion_scoring_pipeline (每日 22:00)
    ↓ 五维度评分 + 话题抑制
raw_events 数据表
    ↓ 数据筛选与排序
summary_generation_dag (每日 23:00)  
    ↓ JSON 摘要生成
exports/ 目录
```

### DAG调度配置（北京时间）

| DAG | 功能 | 调度时间 | Cron表达式 | 状态 |
|-----|------|----------|------------|------|
| ingestion_scoring_pipeline | 新闻采集与评分 | 22:00 | 0 14 * * * | ✅ 运行中 |
| summary_generation_dag | 摘要生成 | 23:00 | 0 15 * * * | ✅ 运行中 |

## 🔧 系统管理

### 常用管理命令

```bash
# 启动服务
docker-compose -f docker-compose.phoenix.yml up -d

# 停止服务
docker-compose -f docker-compose.phoenix.yml down

# 重启服务
docker-compose -f docker-compose.phoenix.yml restart

# 查看服务状态
docker-compose -f docker-compose.phoenix.yml ps

# 查看日志
docker-compose -f docker-compose.phoenix.yml logs
docker-compose -f docker-compose.phoenix.yml logs phoenix-webserver
docker-compose -f docker-compose.phoenix.yml logs phoenix-scheduler

# 手动触发DAG
docker-compose -f docker-compose.phoenix.yml exec phoenix-webserver \
  airflow dags trigger ingestion_scoring_pipeline

docker-compose -f docker-compose.phoenix.yml exec phoenix-webserver \
  airflow dags trigger summary_generation_dag
```

### 数据备份

```bash
# 备份数据库
docker-compose -f docker-compose.phoenix.yml exec postgres-phoenix \
  pg_dump -U phoenix_user phoenix_db > phoenix_backup_$(date +%Y%m%d_%H%M%S).sql

# 备份配置文件
tar -czf phoenix_config_backup_$(date +%Y%m%d_%H%M%S).tar.gz \
  .env docker-compose.phoenix.yml
```

### 系统监控

```bash
# 查看系统资源使用情况
docker stats

# 查看磁盘使用情况
df -h

# 查看内存使用情况
free -h

# 查看网络连接
netstat -tlnp | grep -E ':(8082|5051|5434|6381)'
```

## 🚨 故障排除

### 常见问题

#### 1. 容器启动失败

```bash
# 检查容器状态
docker-compose -f docker-compose.phoenix.yml ps

# 查看错误日志
docker-compose -f docker-compose.phoenix.yml logs

# 检查端口占用
sudo netstat -tlnp | grep -E ':(8082|5051|5434|6381)'
```

#### 2. 数据库连接失败

```bash
# 检查PostgreSQL容器状态
docker-compose -f docker-compose.phoenix.yml logs postgres-phoenix

# 测试数据库连接
docker-compose -f docker-compose.phoenix.yml exec postgres-phoenix \
  psql -U phoenix_user -d phoenix_db -c "SELECT version();"
```

#### 3. API调用失败

```bash
# 检查API密钥配置
docker-compose -f docker-compose.phoenix.yml exec phoenix-webserver \
  airflow variables get ainews_eventregistry_apikeys

# 查看API调用日志
docker-compose -f docker-compose.phoenix.yml logs phoenix-webserver | grep -i "api\|error"
```

#### 4. DAG执行失败

```bash
# 查看DAG执行日志
docker-compose -f docker-compose.phoenix.yml exec phoenix-webserver \
  airflow tasks list ingestion_scoring_pipeline

# 查看任务执行历史
docker-compose -f docker-compose.phoenix.yml exec phoenix-webserver \
  airflow dags state ingestion_scoring_pipeline
```

### 重置系统

```bash
# 完全重置Phoenix系统
docker-compose -f docker-compose.phoenix.yml down -v
docker system prune -f
docker-compose -f docker-compose.phoenix.yml up -d
```

### 日志分析

```bash
# 查看实时日志
docker-compose -f docker-compose.phoenix.yml logs -f

# 查看特定服务的日志
docker-compose -f docker-compose.phoenix.yml logs -f phoenix-webserver

# 查看错误日志
docker-compose -f docker-compose.phoenix.yml logs | grep -i error
```

## 📈 性能优化

### 系统调优

```bash
# 增加Docker内存限制
echo '{"default-ulimits":{"memlock":{"Hard":-1,"Name":"memlock","Soft":-1}}}' | \
  sudo tee /etc/docker/daemon.json

# 重启Docker服务
sudo systemctl restart docker
```

### 数据库优化

```sql
-- 连接数据库
docker-compose -f docker-compose.phoenix.yml exec postgres-phoenix \
  psql -U phoenix_user -d phoenix_db

-- 创建索引优化查询性能
CREATE INDEX IF NOT EXISTS idx_raw_events_score ON raw_events(composite_score DESC);
CREATE INDEX IF NOT EXISTS idx_raw_events_date ON raw_events(created_at);
CREATE INDEX IF NOT EXISTS idx_raw_events_suppressed ON raw_events(is_suppressed);
```

## 🔒 安全建议

### 1. 修改默认密码

```bash
# 修改Airflow管理员密码
docker-compose -f docker-compose.phoenix.yml exec phoenix-webserver \
  airflow users create --username phoenix_admin --firstname Phoenix \
  --lastname Admin --role Admin --email phoenix@example.com \
  --password your_new_password

# 修改pgAdmin密码
# 编辑 .env 文件中的 PGADMIN_DEFAULT_PASSWORD
```

### 2. 配置Nginx反向代理

```nginx
# /etc/nginx/sites-available/phoenix
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8082;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. 启用HTTPS

```bash
# 安装Certbot
sudo apt install certbot python3-certbot-nginx

# 获取SSL证书
sudo certbot --nginx -d your-domain.com
```

## 📞 技术支持

### 获取帮助

- **项目文档**: [GitHub Repository](https://github.com/frankliness/AInews)
- **问题反馈**: [GitHub Issues](https://github.com/frankliness/AInews/issues)
- **系统监控**: 通过Airflow Web界面查看DAG执行状态和日志

### 更新系统

```bash
# 更新代码
cd /opt/phoenix
git pull origin main

# 重新构建并启动服务
docker-compose -f docker-compose.phoenix.yml down
docker-compose -f docker-compose.phoenix.yml up -d --build
```

---

**注意**: 请根据您的实际环境调整配置参数，特别是API密钥设置和网络配置。建议在生产环境中使用HTTPS和强密码，并定期备份数据。