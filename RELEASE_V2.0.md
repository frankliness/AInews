# AInews v2.0.0 发布说明

## 🎉 版本概述

AInews v2.0.0 是一个重大升级版本，引入了独立的 Phoenix 新闻处理系统，同时保持了与 v1.0 的完全兼容性。

## 🚀 主要新功能

### 1. Phoenix 独立系统
- **独立数据库环境**: 专用的 Phoenix PostgreSQL 数据库
- **高级新闻评分**: 基于机器学习的新闻重要性评分系统
- **智能聚类**: 改进的主题聚类和事件关联算法
- **北京时间支持**: 自动时区转换，确保所有时间数据使用北京时间

### 2. 系统架构升级
- **重构的 Airflow DAG**: 更清晰的管道设计和错误处理
- **多源数据整合**: 支持 EventRegistry、NewsAPI、Twitter 等多源数据
- **实时监控**: 完善的日志记录和性能监控
- **JSON 报告生成**: 自动生成结构化的新闻摘要报告

### 3. 数据库和配置管理
- **Phoenix 专用表结构**: 优化的数据库设计
- **时区处理**: 完善的 UTC 到北京时间转换
- **配置系统**: 集中的配置管理
- **数据质量监控**: 自动数据验证和清理

## 🔧 技术升级

### 核心组件
- **Python 3.11**: 升级到最新的 Python 版本
- **Airflow 2.9**: 使用最新的 Airflow 版本
- **PostgreSQL 16**: 升级数据库版本
- **Redis 7**: 最新缓存系统

### 新增工具和脚本
- `scripts/convert_phoenix_timestamps.py`: 时间戳转换工具
- `scripts/validate_api_response.py`: API 响应验证
- `dags/phoenix/advanced_scorer.py`: 高级评分算法
- `dags/phoenix/db_utils.py`: 数据库工具函数

## 📊 性能改进

### 数据处理
- **批量写入优化**: 提高数据库写入效率
- **内存管理**: 优化大数据集处理
- **并发处理**: 支持并行数据抓取
- **缓存机制**: 减少重复 API 调用

### 系统稳定性
- **错误恢复**: 改进的错误处理和重试机制
- **资源监控**: 实时系统资源监控
- **日志管理**: 结构化的日志记录
- **健康检查**: 自动系统健康检查

## 🔄 兼容性

### 向后兼容
- ✅ 完全兼容 v1.0 系统
- ✅ 保持现有数据和工作流程
- ✅ 支持现有 API 接口
- ✅ 兼容现有的配置文件

### 部署选项
- **独立部署**: Phoenix 系统可独立运行
- **集成部署**: 与现有系统集成运行
- **混合部署**: 支持部分功能独立部署

## 📦 安装和部署

### 系统要求
- Docker 和 Docker Compose
- 至少 4GB RAM
- 至少 10GB 可用磁盘空间

### 快速开始
```bash
# 克隆仓库
git clone https://github.com/frankliness/AInews.git
cd AInews

# 切换到 v2.0.0 标签
git checkout v2.0.0

# 启动 Phoenix 系统
docker compose -f docker-compose.phoenix.yml up -d

# 启动主系统（可选）
docker compose up -d
```

### 环境配置
1. 复制 `.env.example` 到 `.env`
2. 配置必要的 API 密钥
3. 设置数据库连接参数
4. 配置时区设置

## 🎯 使用指南

### Phoenix 系统
- **访问地址**: http://localhost:8082
- **数据库**: PostgreSQL (端口 5434)
- **pgAdmin**: http://localhost:5051

### 主系统
- **访问地址**: http://localhost:8080
- **数据库**: PostgreSQL (端口 5432)
- **pgAdmin**: http://localhost:5050

## 🔍 监控和日志

### 日志位置
- Phoenix 系统: `./logs/phoenix/`
- 主系统: `./logs/`
- 数据库日志: Docker 容器日志

### 监控指标
- API 调用次数和成功率
- 数据处理速度和效率
- 系统资源使用情况
- 错误率和恢复时间

## 🐛 已知问题

### 当前限制
- Phoenix 系统需要独立的数据库实例
- 某些高级功能需要额外的 API 配额
- 时区转换仅支持 Asia/Shanghai

### 计划改进
- 支持更多时区
- 增加更多数据源
- 优化内存使用
- 改进错误处理

## 📈 升级路径

### 从 v1.0 升级
1. 备份现有数据
2. 更新代码到 v2.0.0
3. 运行数据库迁移脚本
4. 验证系统功能
5. 切换流量到新版本

### 数据迁移
```bash
# 转换历史时间戳
python scripts/convert_phoenix_timestamps.py

# 验证数据完整性
python scripts/validate_api_response.py
```

## 🤝 贡献指南

### 开发环境
- 使用 Python 3.11
- 遵循 PEP 8 代码规范
- 添加单元测试
- 更新文档

### 提交规范
- 使用语义化提交信息
- 添加详细的变更说明
- 更新相关文档

## 📞 支持和反馈

### 问题报告
- GitHub Issues: https://github.com/frankliness/AInews/issues
- 邮件支持: [联系邮箱]

### 社区
- 技术讨论: GitHub Discussions
- 功能请求: GitHub Issues
- 文档贡献: Pull Requests

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

**发布日期**: 2025年7月30日  
**版本**: v2.0.0  
**维护者**: AInews 开发团队 