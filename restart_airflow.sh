#!/bin/bash

echo "🔄 重启Airflow服务以安装新的依赖包..."

# 停止所有服务
echo "⏹️  停止所有服务..."
docker-compose down

# 删除旧的镜像（可选，强制重新构建）
echo "🗑️  删除旧的Airflow镜像..."
docker rmi apache/airflow:2.9.2-python3.11 2>/dev/null || true

# 重新构建并启动服务
echo "🔨 重新构建并启动服务..."
docker-compose up -d --build

# 等待依赖安装完成
echo "⏳ 等待依赖包安装完成..."
sleep 60

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 30

# 检查服务状态
echo "📊 检查服务状态..."
docker-compose ps

echo "✅ 重启完成！"
echo "🌐 Airflow Web UI: http://localhost:8080"
echo "📊 PgAdmin: http://localhost:5050"
echo ""
echo "如果仍有错误，请检查日志："
echo "docker-compose logs airflow-scheduler"
echo "docker-compose logs airflow-webserver" 