# 版本管理指南

## 🎯 版本管理策略

本项目采用语义化版本控制（Semantic Versioning），格式为 `主版本号.次版本号.修订号`（如 v1.0.0）。

## 📋 当前版本状态

### v1.0.0 - 生产基础版本 ✅
- **状态**: 生产就绪
- **功能**: 完整的时政视频账号新闻去同质化系统
- **提交**: `fdce61d`
- **标签**: `v1.0.0`

### v2.0.0 - Phoenix 独立系统升级 ✅
- **状态**: 生产就绪
- **功能**: Phoenix 独立系统 + 北京时间支持 + 高级评分算法
- **提交**: `588ea07`
- **标签**: `v2.0.0`

### v2.1.0 - 生产就绪版本 ✅
- **状态**: 生产就绪
- **功能**: 完善 API Key 管理系统 + 修复 EventRegistryError + 优化 Phoenix 客户端
- **提交**: `e684441`
- **标签**: `v2.1.0`
- **发布日期**: 2025年1月24日

## 🔄 版本管理方法

### 1. 创建版本标签

```bash
# 创建带注释的标签
git tag -a v1.0.0 -m "生产版本 v1.0.0 - 时政视频账号新闻去同质化系统基础版本"

# 推送标签到远程仓库
git push origin v1.0.0
```

### 2. 查看所有版本

```bash
# 查看所有标签
git tag -l

# 查看标签详细信息
git show v1.0.0
```

### 3. 回滚到指定版本

#### 方法A：临时回滚（推荐用于测试）
```bash
# 切换到指定版本进行测试
git checkout v1.0.0

# 返回最新版本
git checkout main
```

#### 方法B：创建回滚分支
```bash
# 基于v1.0.0创建新分支
git checkout -b rollback-v1.0.0 v1.0.0

# 推送回滚分支
git push origin rollback-v1.0.0
```

#### 方法C：强制回滚主分支（谨慎使用）
```bash
# 重置到指定版本
git reset --hard v1.0.0

# 强制推送到远程（会丢失后续提交）
git push --force origin main
```

### 4. 开发新功能

```bash
# 创建功能分支
git checkout -b feature/new-feature

# 开发完成后合并
git checkout main
git merge feature/new-feature

# 删除功能分支
git branch -d feature/new-feature
```

## 🏷️ 版本命名规范

### 主版本号（Major）
- 不兼容的API修改
- 重大架构变更
- 示例：v1.0.0 → v2.0.0

### 次版本号（Minor）
- 向下兼容的功能性新增
- 新功能添加
- 示例：v1.0.0 → v1.1.0

### 修订号（Patch）
- 向下兼容的问题修正
- Bug修复
- 示例：v1.0.0 → v1.0.1

## 📝 版本发布流程

### 1. 开发阶段
```bash
# 在功能分支上开发
git checkout -b feature/optimization
# ... 开发代码 ...
git add .
git commit -m "feat: 添加新功能"
```

### 2. 测试阶段
```bash
# 合并到测试分支
git checkout test
git merge feature/optimization
# ... 进行测试 ...
```

### 3. 发布阶段
```bash
# 合并到主分支
git checkout main
git merge feature/optimization

# 创建新版本标签
git tag -a v1.1.0 -m "版本 v1.1.0 - 新增功能"
git push origin v1.1.0
```

## 🚨 紧急回滚流程

### 场景：新版本出现问题，需要快速回滚

```bash
# 1. 立即切换到稳定版本
git checkout v1.0.0

# 2. 创建紧急回滚分支
git checkout -b hotfix/emergency-rollback

# 3. 推送到远程
git push origin hotfix/emergency-rollback

# 4. 通知团队使用回滚分支
```

## 📊 版本历史记录

| 版本 | 日期 | 状态 | 主要功能 |
|------|------|------|----------|
| v1.0.0 | 2025-01-24 | ✅ 生产 | 基础新闻去同质化系统 |
| v1.1.0 | 计划中 | 🔄 开发 | 性能优化 |
| v1.2.0 | 计划中 | 📋 规划 | 新功能扩展 |

## 🔧 实用命令

### 查看版本差异
```bash
# 查看两个版本之间的差异
git diff v1.0.0 v1.1.0

# 查看特定文件的版本差异
git diff v1.0.0 v1.1.0 -- config.yaml
```

### 查看提交历史
```bash
# 查看从v1.0.0到现在的所有提交
git log v1.0.0..HEAD --oneline

# 查看特定版本的提交
git log v1.0.0 -1
```

### 清理分支
```bash
# 删除本地分支
git branch -d feature/old-feature

# 删除远程分支
git push origin --delete feature/old-feature
```

## ⚠️ 注意事项

1. **强制推送谨慎使用**: `git push --force` 会丢失历史记录
2. **重要版本备份**: 生产版本建议创建备份分支
3. **测试充分**: 新版本发布前必须充分测试
4. **文档同步**: 版本更新时同步更新文档
5. **团队沟通**: 重大版本变更需要团队协调

## 🎯 推荐工作流程

1. **开发新功能**: 在功能分支上开发
2. **充分测试**: 在测试环境验证
3. **创建版本**: 测试通过后创建新版本标签
4. **部署生产**: 部署到生产环境
5. **监控运行**: 监控生产环境运行状态
6. **准备回滚**: 随时准备回滚到稳定版本

---

**当前稳定版本**: v1.0.0  
**最后更新**: 2025-01-24  
**维护者**: 开发团队 