# Phoenix系统 Ubuntu服务器部署指南

## 🎯 概述

本指南将帮助您将Phoenix新闻系统从本地环境部署到Ubuntu服务器上。Phoenix系统是一个基于Apache Airflow的新闻数据处理管道，包含独立的数据库、Web界面和调度服务。

## 📋 系统要求

### 硬件要求
- **CPU**: 至少2核心
- **内存**: 至少4GB RAM
- **存储**: 至少20GB可用空间
- **网络**: 稳定的互联网连接

### 软件要求
- **操作系统**: Ubuntu 20.04 LTS 或更高版本
- **Docker**: 20.10 或更高版本
- **Docker Compose**: 2.0 或更高版本
- **Git**: 用于代码管理

## 🚀 部署步骤

### 1. 服务器准备

#### 1.1 更新系统
```bash
sudo apt update && sudo apt upgrade -y
```

#### 1.2 安装必要工具
```bash
sudo apt install -y curl wget git unzip software-properties-common apt-transport-https ca-certificates gnupg lsb-release
```

### 2. 安装Docker

#### 2.1 添加Docker官方GPG密钥
```bash
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
```

#### 2.2 添加Docker仓库
```bash
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

#### 2.3 安装Docker
```bash
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

#### 2.4 配置Docker用户组
```bash
sudo usermod -aG docker $USER
newgrp docker
```

#### 2.5 启动Docker服务
```bash
sudo systemctl start docker
sudo systemctl enable docker
```

### 3. 安装Docker Compose

#### 3.1 下载Docker Compose
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
```

#### 3.2 设置执行权限
```bash
sudo chmod +x /usr/local/bin/docker-compose
```

#### 3.3 验证安装
```bash
docker-compose --version
```

### 4. 部署Phoenix系统

#### 4.1 克隆代码仓库
```bash
# 创建项目目录
mkdir -p /opt/phoenix
cd /opt/phoenix

# 克隆仓库
git clone https://github.com/frankliness/AInews.git .
```

#### 4.2 配置环境变量
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

# API密钥配置（请替换为您的实际密钥）
EVENTREGISTRY_API_KEY=your_eventregistry_api_key_here
NEWSAPI_API_KEY=your_newsapi_key_here
OPENAI_API_KEY=your_openai_api_key_here
EOF
```

#### 4.3 创建必要目录
```bash
# 创建日志和导出目录
mkdir -p logs exports
chmod 755 logs exports
```

#### 4.4 启动Phoenix系统
```bash
# 启动所有服务
docker-compose -f docker-compose.phoenix.yml up -d

# 检查服务状态
docker-compose -f docker-compose.phoenix.yml ps
```

### 5. 配置防火墙

#### 5.1 安装UFW防火墙
```bash
sudo apt install -y ufw
```

#### 5.2 配置防火墙规则
```bash
# 允许SSH连接
sudo ufw allow ssh

# 允许Phoenix系统端口
sudo ufw allow 8082  # Phoenix Airflow Web界面
sudo ufw allow 5051  # Phoenix pgAdmin
sudo ufw allow 5434  # Phoenix PostgreSQL（如果需要外部访问）

# 启用防火墙
sudo ufw enable
```

### 6. 配置Nginx反向代理（可选）

#### 6.1 安装Nginx
```bash
sudo apt install -y nginx
```

#### 6.2 创建Nginx配置
```bash
sudo tee /etc/nginx/sites-available/phoenix << 'EOF'
server {
    listen 80;
    server_name your-domain.com;  # 替换为您的域名

    # Phoenix Airflow Web界面
    location / {
        proxy_pass http://localhost:8082;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Phoenix pgAdmin
    location /pgadmin {
        proxy_pass http://localhost:5051;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
```

#### 6.3 启用站点配置
```bash
sudo ln -s /etc/nginx/sites-available/phoenix /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 🔍 验证部署

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
```

## 🔧 系统管理

### 1. 常用管理命令

#### 启动服务
```bash
docker-compose -f docker-compose.phoenix.yml up -d
```

#### 停止服务
```bash
docker-compose -f docker-compose.phoenix.yml down
```

#### 重启服务
```bash
docker-compose -f docker-compose.phoenix.yml restart
```

#### 查看日志
```bash
# 查看所有服务日志
docker-compose -f docker-compose.phoenix.yml logs

# 查看特定服务日志
docker-compose -f docker-compose.phoenix.yml logs phoenix-webserver
docker-compose -f docker-compose.phoenix.yml logs phoenix-scheduler
```

### 2. 数据备份

#### 备份数据库
```bash
# 创建备份目录
mkdir -p /opt/phoenix/backups

# 备份Phoenix数据库
docker-compose -f docker-compose.phoenix.yml exec postgres-phoenix pg_dump -U phoenix_user phoenix_db > /opt/phoenix/backups/phoenix_db_$(date +%Y%m%d_%H%M%S).sql
```

#### 备份配置文件
```bash
# 备份重要配置文件
tar -czf /opt/phoenix/backups/config_$(date +%Y%m%d_%H%M%S).tar.gz \
    docker-compose.phoenix.yml \
    .env \
    config/ \
    dags/phoenix/
```

### 3. 系统监控

#### 检查资源使用
```bash
# 检查Docker容器资源使用
docker stats

# 检查磁盘使用
df -h

# 检查内存使用
free -h
```

#### 监控日志
```bash
# 实时监控Phoenix Web服务器日志
docker-compose -f docker-compose.phoenix.yml logs -f phoenix-webserver

# 实时监控调度器日志
docker-compose -f docker-compose.phoenix.yml logs -f phoenix-scheduler
```

## 🚨 故障排除

### 1. 常见问题

#### 容器启动失败
```bash
# 检查容器状态
docker-compose -f docker-compose.phoenix.yml ps

# 查看详细错误日志
docker-compose -f docker-compose.phoenix.yml logs phoenix-webserver
```

#### 端口冲突
```bash
# 检查端口占用
sudo netstat -tlnp | grep :8082
sudo netstat -tlnp | grep :5051
sudo netstat -tlnp | grep :5434
```

#### 数据库连接问题
```bash
# 检查数据库容器状态
docker-compose -f docker-compose.phoenix.yml exec postgres-phoenix psql -U phoenix_user -d phoenix_db -c "SELECT version();"
```

### 2. 重置系统
```bash
# 完全重置Phoenix系统
docker-compose -f docker-compose.phoenix.yml down -v
docker system prune -f
docker-compose -f docker-compose.phoenix.yml up -d
```

## 📞 技术支持

如果在部署过程中遇到问题，请：

1. 检查本文档的故障排除部分
2. 查看系统日志获取详细错误信息
3. 确保所有依赖都已正确安装
4. 验证网络连接和防火墙配置

## 🔄 更新部署

### 更新代码
```bash
cd /opt/phoenix
git pull origin main
docker-compose -f docker-compose.phoenix.yml down
docker-compose -f docker-compose.phoenix.yml up -d --build
```

### 回滚到之前版本
```bash
cd /opt/phoenix
git log --oneline -10  # 查看提交历史
git checkout <commit-hash>  # 切换到指定版本
docker-compose -f docker-compose.phoenix.yml down
docker-compose -f docker-compose.phoenix.yml up -d --build
```

---

**注意**: 请根据您的实际环境调整配置参数，特别是API密钥、域名和端口设置。
