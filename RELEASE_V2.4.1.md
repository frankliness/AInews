# AInews v2.4.1 发布说明

## 🎯 版本概述

v2.4.1 是一个系统配置优化版本，主要针对调度时间和文件输出路径进行了优化，提升了系统的运维便利性和文件管理效率。

## 🚀 主要优化

### 1. 调度时间优化

#### 修改前
- **DAG**: `ingestion_scoring_pipeline`
- **调度时间**: `'0 2,9,14 * * *'` (每天3次：北京时间10:00, 17:00, 22:00)
- **描述**: "高频运行的新闻抓取与高级打分流水线"

#### 修改后
- **DAG**: `ingestion_scoring_pipeline`
- **调度时间**: `'0 14 * * *'` (每天1次：北京时间22:00)
- **描述**: "每日运行的新闻抓取与高级打分流水线"

#### 优化效果
- **资源消耗**: 减少66%的系统资源消耗
- **API调用**: 降低API调用频率，避免配额浪费
- **运维管理**: 简化调度管理，便于监控和维护
- **数据质量**: 适合每日汇总分析，确保数据完整性

### 2. 文件输出路径修复

#### 问题描述
`summary_generation_dag` 的JSON报告文件输出到了根目录外一层的 `Jiuwanli/exports` 目录，而不是项目目录内的 `Jiuwanli/dev/exports`。

#### 根本原因
Docker配置中的卷挂载设置：
```yaml
# 修改前
- ../exports:/opt/airflow/exports  # 输出到 Jiuwanli/exports

# 修改后  
- ./exports:/opt/airflow/exports   # 输出到 Jiuwanli/dev/exports
```

#### 修复措施
1. **修改Docker配置**: 将卷挂载从 `../exports` 改为 `./exports`
2. **创建目录**: 在 `dev` 目录下创建 `exports` 目录
3. **重启容器**: 重启Docker容器以应用新配置

#### 修复效果
- **文件位置**: JSON报告现在正确输出到 `Jiuwanli/dev/exports/`
- **目录结构**: 保持项目文件在项目目录内，便于管理
- **向后兼容**: 不影响现有代码逻辑，`json_report_generator.py` 中的路径保持不变

## 📁 修改文件

### 核心配置
- `dags/phoenix/ingestion_scoring_pipeline_dag.py` - 修改DAG调度时间
- `docker-compose.phoenix.yml` - 修复卷挂载配置
- `notes` - 更新系统优化记录

### 新增目录
- `exports/` - 创建本地exports目录用于文件输出

## 🔧 技术细节

### 调度时间说明
- **UTC时间**: 14:00 (下午2点)
- **北京时间**: 22:00 (晚上10点)
- **运行频率**: 每天一次
- **时区转换**: UTC +8 = 北京时间

### 卷挂载配置
```yaml
# phoenix-webserver 和 phoenix-scheduler 服务
volumes:
  - ./dags/phoenix:/opt/airflow/dags/phoenix
  - ./config:/opt/airflow/config
  - ./scraper:/opt/airflow/scraper
  - ./sql:/opt/airflow/sql
  - ./utils:/opt/airflow/utils
  - ./logs:/opt/airflow/logs
  - phoenix_logs:/opt/airflow/logs
  - ./exports:/opt/airflow/exports  # 修复后的配置
```

## 🚀 部署指南

### 1. 应用配置更改
```bash
# 重启Docker容器以应用新配置
docker-compose -f docker-compose.phoenix.yml down
docker-compose -f docker-compose.phoenix.yml up -d
```

### 2. 验证调度时间
在Airflow UI中检查 `ingestion_scoring_pipeline` DAG的调度时间是否正确设置为每天22:00。

### 3. 验证文件输出
运行 `summary_generation_dag` 并检查JSON报告是否输出到 `Jiuwanli/dev/exports/` 目录。

## 📊 性能影响

### 正面影响
- **资源使用**: 减少66%的CPU和内存使用
- **API配额**: 降低API调用频率，延长配额使用周期
- **存储空间**: 减少重复数据存储，节省磁盘空间
- **运维成本**: 简化监控和维护工作

### 注意事项
- **数据实时性**: 数据更新频率从每天3次降低到1次
- **监控调整**: 需要相应调整监控告警的时间窗口
- **备份策略**: 确保单次运行能处理足够的数据量

## 🧪 验证方法

### 调度时间验证
```bash
# 检查DAG配置
docker-compose -f docker-compose.phoenix.yml exec phoenix-webserver airflow dags list | grep ingestion_scoring_pipeline
```

### 文件输出验证
```bash
# 检查exports目录
ls -la exports/

# 手动触发summary_generation_dag并检查输出
docker-compose -f docker-compose.phoenix.yml exec phoenix-webserver airflow dags trigger summary_generation_dag
```

## 🔄 回滚方案

如需回滚到v2.4.0：
1. 恢复DAG调度时间为每天3次运行
2. 恢复Docker卷挂载配置
3. 重新部署v2.4.0版本

## 📝 更新日志

### v2.4.1 (2025-08-05)
- ⚡ 优化ingestion_scoring_pipeline调度时间为每天22:00运行
- 🐛 修复summary_generation_dag文件输出路径问题
- 🔧 更新Docker卷挂载配置
- 📚 完善系统优化文档
- 📁 创建本地exports目录

### 与v2.4.0的差异
- **调度优化**: 从每天3次改为每天1次运行
- **路径修复**: 文件输出路径从根目录外改为项目目录内
- **配置优化**: 改进Docker卷挂载配置
- **文档完善**: 更新系统优化记录

---

**发布日期**: 2025-08-05  
**版本号**: v2.4.1  
**兼容性**: 向后兼容v2.4.0  
**升级建议**: 推荐升级，优化系统资源使用和文件管理
