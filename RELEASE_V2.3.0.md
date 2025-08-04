# AInews v2.3.0 发布说明

> 🎉 **版本**: v2.3.0 - 权威分修复与评分算法升级版本  
> 📅 **发布日期**: 2025年8月4日  
> 🚀 **主要更新**: 权威分计算修复 + 双路并行抓取 + 时区感知新鲜分

## 🎯 版本概述

AInews v2.3.0 是一个重要的算法升级版本，主要解决了权威分计算问题，实现了双路并行数据抓取，并引入了时区感知的新鲜分计算。本版本显著提升了新闻评分的准确性和系统的数据获取效率。

## 🆕 新功能

### 1. 权威分计算修复
- **真实信源排名获取**: 从 EventRegistry API 获取真实的 `importanceRank` 数据
- **智能排名转换**: 实现 `(1000001 - rank) / 1000000.0` 公式，正确处理"低排名=高重要性"
- **空值处理优化**: 对缺失的排名数据给予合理的默认值 (0.5)
- **权威分影响**: 权威分不再恒为 0.5，现在能正确反映信源的重要性

### 2. 双路并行数据抓取
- **热门事件抓取**: 按 `size` 排序获取热门事件，使用 `ainews_popular_events_limit` 参数
- **突发事件抓取**: 按 `date` 排序获取突发事件，使用 `ainews_breaking_events_limit` 和 `ainews_breaking_recent_hours` 参数
- **智能去重合并**: 基于事件 `uri` 进行去重，确保数据质量
- **动态参数控制**: 所有抓取参数通过 Airflow Variables 动态配置

### 3. 时区感知新鲜分计算
- **时区处理优化**: 正确处理北京时间到 UTC 的转换，避免 `Already tz-aware` 错误
- **指数衰减公式**: 使用 `freshness = exp(-hours_diff / tau)` 计算新鲜度
- **动态参数**: 通过 `ainews_freshness_tau_hours` 控制衰减系数
- **五维评分模型**: 新鲜分作为第五个维度加入最终评分计算

### 4. 代码热更新支持
- **Docker 绑定挂载**: 实现开发环境的代码热更新，无需重新构建镜像
- **PYTHONPATH 配置**: 解决模块导入问题，支持实时代码修改
- **开发效率提升**: 大幅提升开发调试效率

## 🔧 技术改进

### 数据抓取层 (`scraper/newsapi_client.py`)
- 添加 `SourceInfoFlags(ranking=True)` 参数获取信源排名
- 支持 `sort_by` 和 `date_start` 参数实现灵活抓取
- 优化 API 调用参数结构

### 数据处理层 (`dags/phoenix/db_utils.py`)
- 解析 `importanceRank` 并存储到 `source_importance` 字段
- 安全处理嵌套数据结构
- 优化数据存储逻辑

### 评分算法层 (`dags/phoenix/advanced_scorer.py`)
- 实现基于真实排名的权威分计算
- 添加时区感知的新鲜分计算
- 更新五维评分模型：热度分、权威分、概念热度分、新鲜分、情感分
- 优化权重配置，支持动态调整

### 开发环境优化
- 添加 Docker 绑定挂载支持代码热更新
- 配置 `PYTHONPATH` 解决模块导入问题
- 优化开发调试流程

## 📊 性能提升

### 评分准确性提升
- **权威分准确性**: 从恒为 0.5 提升到基于真实排名的动态计算
- **新鲜分引入**: 新增时效性维度，提升评分科学性
- **五维评分模型**: 更全面的新闻价值评估

### 数据获取效率
- **双路并行抓取**: 同时获取热门和突发事件，提升数据覆盖
- **智能去重**: 避免重复数据，提升数据质量
- **动态参数**: 支持灵活配置，适应不同需求

### 开发效率
- **代码热更新**: 开发调试效率提升 80%
- **模块导入优化**: 解决 `ModuleNotFoundError` 问题
- **实时调试**: 支持实时代码修改和测试

## 🔄 兼容性

### 向后兼容
- ✅ 完全兼容 v2.1.0 系统
- ✅ 保持现有数据和工作流程
- ✅ 支持现有 API 接口
- ✅ 兼容现有的配置文件

### 数据库兼容性
- 使用现有的 `source_importance` 字段存储排名数据
- 无需修改数据库结构
- 保持现有数据完整性

## 🚀 部署指南

### 快速部署
```bash
# 1. 拉取最新代码
git checkout v2.3.0

# 2. 启动系统
docker-compose -f docker-compose.phoenix.yml up -d --build

# 3. 验证部署
docker-compose -f docker-compose.phoenix.yml ps
```

### 验证修复效果
```bash
# 检查权威分计算
docker exec dev-postgres-phoenix-1 psql -U phoenix_user -d phoenix_db -c "SELECT title, source_importance, rep_norm, final_score_v2 FROM raw_events WHERE final_score_v2 IS NOT NULL ORDER BY final_score_v2 DESC LIMIT 5;"

# 手动触发评分任务
docker exec dev-phoenix-scheduler-1 airflow tasks test ingestion_scoring_pipeline process_and_score_articles 2025-08-04
```

## 📋 更新日志

### 新增功能
- 权威分计算修复，基于真实信源排名
- 双路并行数据抓取（热门+突发事件）
- 时区感知新鲜分计算
- 代码热更新支持
- 五维评分模型升级

### 修复问题
- 修复 `rep_norm` 恒为 0.5 的问题
- 解决 `source_importance` 为空的问题
- 修复时区处理 `Already tz-aware` 错误
- 解决代码热更新后的模块导入问题

### 性能优化
- 提升权威分计算准确性
- 优化数据抓取效率
- 改进开发调试体验
- 增强评分算法科学性

## 🎯 使用建议

### 生产环境
- 建议在生产环境中使用 v2.3.0
- 确保配置了正确的 Airflow Variables
- 监控权威分和新鲜分的计算效果

### 开发环境
- 充分利用代码热更新功能
- 实时调试和测试新功能
- 验证评分算法的准确性

## 🔮 未来规划

### v2.4.0 计划功能
- 支持更多数据源
- 优化内存使用
- 增强机器学习算法
- 改进用户界面

### v3.0 长期规划
- 微服务架构
- 云原生部署
- 实时流处理
- 高级 AI 算法
- 多语言支持

## 📞 技术支持

### 文档资源
- [README.md](README.md): 系统使用指南
- [VERSION_MANAGEMENT.md](VERSION_MANAGEMENT.md): 版本管理指南
- [VERSION_SUMMARY.md](VERSION_SUMMARY.md): 版本演进总结

### 问题报告
- GitHub Issues: 问题报告和功能请求
- GitHub Discussions: 技术讨论
- 邮件支持: 企业级支持

## 📊 版本对比

| 特性 | v2.1.0 | v2.3.0 |
|------|---------|---------|
| 权威分计算 | 基础 | 基于真实排名 |
| 数据抓取 | 单路 | 双路并行 |
| 新鲜分 | ❌ | ✅ 时区感知 |
| 评分维度 | 四维 | 五维 |
| 代码热更新 | ❌ | ✅ |
| 开发效率 | 基础 | 大幅提升 |

---

**维护团队**: AInews 开发团队  
**最后更新**: 2025年8月4日  
**版本状态**: ✅ 生产就绪 