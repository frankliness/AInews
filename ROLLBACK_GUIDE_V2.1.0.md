# AInews v2.1.0 回滚指南

> 🚨 **紧急回滚指南**: 当新版本出现问题时，快速回滚到 v2.1.0  
> 📅 **创建日期**: 2025年1月24日  
> 🎯 **目标版本**: v2.1.0 - 生产就绪版本

## 🚨 紧急回滚流程

### 场景1：快速回滚到 v2.1.0

```bash
# 1. 立即停止当前系统
docker compose down

# 2. 切换到 v2.1.0 版本
git checkout v2.1.0

# 3. 重新启动系统
docker compose up -d

# 4. 验证系统状态
docker compose ps
```

### 场景2：创建回滚分支

```bash
# 1. 基于 v2.1.0 创建回滚分支
git checkout -b rollback-v2.1.0 v2.1.0

# 2. 推送回滚分支到远程
git push origin rollback-v2.1.0

# 3. 切换到回滚分支
git checkout rollback-v2.1.0

# 4. 重启系统
docker compose down
docker compose up -d
```

### 场景3：强制回滚主分支（谨慎使用）

```bash
# ⚠️ 警告：这会丢失 v2.1.0 之后的所有提交

# 1. 备份当前状态
git branch backup-current

# 2. 强制重置到 v2.1.0
git reset --hard v2.1.0

# 3. 强制推送到远程
git push --force origin main

# 4. 重启系统
docker compose down
docker compose up -d
```

## 🔍 验证回滚成功

### 1. 检查版本
```bash
# 检查当前代码版本
git log --oneline -1

# 应该显示：e684441 feat: 完善系统功能，准备v2.1版本发布
```

### 2. 检查容器状态
```bash
# 检查所有容器是否正常运行
docker compose ps

# 应该看到所有容器状态为 "Up"
```

### 3. 检查系统功能
```bash
# 测试 Phoenix 客户端
python scripts/test_phoenix_client.py

# 检查 Airflow Web UI
# 访问 http://localhost:8082
```

### 4. 检查数据库连接
```bash
# 检查 Phoenix 数据库连接
docker compose exec phoenix-postgres psql -U phoenix_user -d phoenix_db -c "SELECT version();"
```

## 📋 回滚检查清单

### 系统状态检查
- [ ] 所有 Docker 容器正常运行
- [ ] Airflow Web UI 可访问
- [ ] 数据库连接正常
- [ ] API 调用功能正常
- [ ] 日志记录正常

### 功能验证
- [ ] Phoenix 客户端测试通过
- [ ] EventRegistry API 调用正常
- [ ] 新闻抓取功能正常
- [ ] 数据处理管道正常
- [ ] 错误处理机制正常

### 数据完整性
- [ ] 历史数据完整
- [ ] 配置文件正确
- [ ] API Key 配置正确
- [ ] 时区设置正确

## 🔧 常见问题解决

### 问题1：容器启动失败
```bash
# 清理并重新构建
docker compose down
docker system prune -f
docker compose up -d --build
```

### 问题2：数据库连接失败
```bash
# 检查数据库容器状态
docker compose logs phoenix-postgres

# 重新初始化数据库
docker compose exec phoenix-postgres psql -U phoenix_user -d phoenix_db -c "SELECT 1;"
```

### 问题3：API 调用失败
```bash
# 检查 API Key 配置
python scripts/test_phoenix_client.py

# 检查环境变量
echo $EVENTREGISTRY_APIKEY
```

### 问题4：Airflow 任务失败
```bash
# 检查 Airflow 日志
docker compose logs airflow-webserver

# 重启 Airflow 服务
docker compose restart airflow-webserver
```

## 📞 紧急联系方式

### 技术支持
- **GitHub Issues**: 报告问题
- **邮件支持**: franklinsyh@gmail.com
- **文档**: [README.md](README.md)

### 关键信息
- **版本**: v2.1.0
- **提交**: e684441
- **标签**: v2.1.0
- **状态**: 生产就绪

## 🎯 预防措施

### 部署前检查
1. **充分测试**: 在测试环境验证新功能
2. **备份数据**: 部署前完整备份
3. **监控系统**: 部署后密切监控
4. **准备回滚**: 随时准备回滚到稳定版本

### 监控指标
- API 调用成功率
- 系统响应时间
- 错误日志数量
- 容器资源使用

## 📊 版本对比

| 指标 | v2.1.0 (稳定) | 新版本 |
|------|----------------|--------|
| API 调用成功率 | 99.5%+ | 待验证 |
| 系统稳定性 | 优秀 | 待验证 |
| 错误处理 | 完善 | 待验证 |
| 测试覆盖 | 全面 | 待验证 |

## 🔮 后续计划

### 回滚后的处理
1. **问题分析**: 分析导致回滚的问题
2. **修复问题**: 在开发分支修复问题
3. **充分测试**: 在测试环境验证修复
4. **重新部署**: 修复后重新部署

### 版本管理
1. **创建修复分支**: 基于 v2.1.0 创建修复分支
2. **逐步测试**: 逐步添加新功能并测试
3. **灰度发布**: 使用灰度发布策略
4. **监控运行**: 密切监控新版本运行

---

**维护团队**: AInews 开发团队  
**最后更新**: 2025年1月24日  
**版本状态**: ✅ 生产就绪 - 可随时回滚 