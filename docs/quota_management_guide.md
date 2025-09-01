# EventRegistry API 配额管理指南

## 概述

本文档描述了如何管理和监控 EventRegistry API 的配额使用情况，避免配额耗尽导致的系统故障。

## 问题描述

### 常见错误
```
Exception: You have used all available tokens for unsubscribed users. 
In order to continue using Event Registry please subscribe to a paid plan.
```

### 错误原因
1. **免费用户配额限制**：EventRegistry 对免费用户有严格的配额限制
2. **配额监控不足**：缺乏有效的配额监控和预警机制
3. **错误处理不完善**：没有针对配额耗尽的特殊处理逻辑

## 解决方案

### 1. 增强的配额检查

我们实现了 `check_api_quota()` 方法，提供详细的配额状态信息：

```python
quota_status = client.check_api_quota()
if not quota_status["can_proceed"]:
    raise Exception(f"API quota check failed: {quota_status.get('error')}")
```

### 2. 配额状态分类

- **sufficient**: 配额充足 (>50)
- **low**: 配额较低 (≤20)
- **critical**: 配额临界 (≤5)
- **exhausted**: 配额耗尽 (=0)
- **unknown**: 无法确定配额状态 (-1)

### 3. 自动API Key轮换

当检测到配额相关错误时，系统会自动轮换到下一个可用的API Key：

```python
if "used all available tokens" in error_message:
    self._rotate_key()
    continue
```

### 4. 配额监控和告警

在DAG运行过程中实时监控配额使用情况：

```python
if requests_after <= 5:
    log.error(f"⚠️ CRITICAL: API quota critically low: {requests_after}")
elif requests_after <= 20:
    log.warning(f"⚠️ WARNING: API quota low: {requests_after}")
```

## 使用方法

### 1. 运行配额检查脚本

```bash
cd scripts
python monitor_quota.py
```

### 2. 在DAG中使用配额检查

```python
# 运行前检查配额
quota_status = client.check_api_quota()
if not quota_status["can_proceed"]:
    raise Exception("Insufficient API quota")

# 运行后监控配额
if requests_after <= 5:
    log.error("配额严重不足，需要立即处理")
```

### 3. 配置配额阈值

编辑 `config/quota_config.yaml` 文件：

```yaml
quota_management:
  thresholds:
    critical_low: 5
    low: 20
    warning: 50
```

## 最佳实践

### 1. 配额规划

- **预留安全余量**：始终保持至少5-10个配额作为安全余量
- **分批处理**：将大量请求分批处理，避免一次性消耗过多配额
- **优先级管理**：优先处理重要的API调用，非必要的调用可以延迟

### 2. 监控策略

- **实时监控**：在每次API调用前后检查配额状态
- **告警设置**：设置不同级别的配额告警
- **日志记录**：详细记录配额使用情况，便于分析和优化

### 3. 错误处理

- **优雅降级**：配额不足时，系统应该能够优雅地降级或停止
- **自动重试**：在配额重置后自动重试失败的请求
- **用户通知**：及时通知用户配额状态和系统状态

## 故障排除

### 1. 配额耗尽

**症状**：API调用返回配额耗尽错误

**解决方案**：
- 检查所有API Key的状态
- 等待配额重置（通常是24小时）
- 考虑升级到付费计划
- 减少API调用频率

### 2. 配额状态未知

**症状**：`getRemainingAvailableRequests()` 返回 -1

**解决方案**：
- 检查API Key的有效性
- 验证网络连接
- 查看EventRegistry服务状态

### 3. 配额消耗过快

**症状**：配额在短时间内快速消耗

**解决方案**：
- 检查是否有重复的API调用
- 优化请求参数，减少不必要的数据获取
- 实现请求缓存机制
- 分析配额使用模式，找出优化点

## 升级建议

### 1. 短期解决方案

- 实施配额监控和告警
- 优化API调用策略
- 实现API Key轮换机制

### 2. 长期解决方案

- 升级到EventRegistry付费计划
- 实施更智能的配额分配算法
- 建立配额使用分析和预测系统

## 联系支持

如果遇到配额相关问题，请：

1. 检查本文档的故障排除部分
2. 运行配额检查脚本获取详细信息
3. 查看系统日志了解具体错误
4. 联系开发团队获取进一步支持

---

*最后更新：2025-08-19*
