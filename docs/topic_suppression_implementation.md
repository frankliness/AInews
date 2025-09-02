# 双重话题抑制功能实现文档

## 概述

本文档描述了AInews系统中"双重话题抑制"功能的实现，该功能通过智能降权机制优化选题聚焦度，确保系统高度聚焦于"政治、经济、外交、军事"等核心领域。

## 功能设计

### 双重抑制机制

1. **常规话题抑制**
   - 目标：对加沙、俄乌战争等持续热点话题的常规报道进行降权
   - 保护机制：通过新鲜度阈值识别"爆点"新闻，避免误杀重要新闻
   - 抑制强度：0.3（可配置）

2. **领域话题降权**
   - 目标：对文体娱乐等非核心领域的新闻进行降权
   - 降权强度：0.5（可配置）
   - 互斥性：只对不属于常规话题的文章应用此规则

### 技术实现

#### 高性能向量化方案

- **布尔掩码**：使用pandas的布尔掩码进行高效的批量筛选
- **集合操作**：通过集合交集检查快速识别话题类型
- **向量化操作**：避免Python循环，确保最佳性能

#### 核心算法流程

```python
# 1. 创建概念集合
concept_sets = df['concepts'].apply(lambda concepts_list: {concept['uri'] for concept in concepts_list})

# 2. 生成布尔掩码
routine_mask = concept_sets.apply(lambda s: not s.isdisjoint(routine_topic_uris))
category_mask = concept_sets.apply(lambda s: not s.isdisjoint(downweight_category_uris))
breaking_mask = df['freshness_score'] >= freshness_threshold

# 3. 应用抑制逻辑
df.loc[routine_mask & ~breaking_mask, 'hot_norm'] *= routine_damping
df.loc[category_mask & ~routine_mask, 'hot_norm'] *= category_damping
```

## 配置参数

### Airflow Variables

| 变量名 | 描述 | 默认值 | 示例 |
|--------|------|--------|------|
| `ainews_routine_topic_uris` | 常规话题URI列表 | `[]` | `["http://en.wikipedia.org/wiki/Gaza_Strip"]` |
| `ainews_downweight_category_uris` | 领域话题URI列表 | `[]` | `["http://en.wikipedia.org/wiki/Arts"]` |
| `ainews_routine_topic_damping_factor` | 常规话题抑制强度 | `0.3` | `0.3` |
| `ainews_category_damping_factor` | 领域话题降权强度 | `0.5` | `0.5` |
| `ainews_freshness_threshold_for_breaking` | 爆点识别阈值 | `0.8` | `0.8` |

### 配置示例

```json
// ainews_routine_topic_uris
[
  "http://en.wikipedia.org/wiki/Gaza_Strip",
  "http://en.wikipedia.org/wiki/Israel–Hamas_war",
  "http://en.wikipedia.org/wiki/Russo-Ukrainian_War",
  "http://en.wikipedia.org/wiki/Russian_invasion_of_Ukraine"
]

// ainews_downweight_category_uris
[
  "http://en.wikipedia.org/wiki/Arts",
  "http://en.wikipedia.org/wiki/Culture",
  "http://en.wikipedia.org/wiki/Entertainment",
  "http://en.wikipedia.org/wiki/Sport"
]
```

## 监控指标

### 新增监控字段

| 字段名 | 类型 | 描述 |
|--------|------|------|
| `is_routine_topic` | boolean | 是否属于常规话题 |
| `is_category_topic` | boolean | 是否属于领域话题 |
| `is_breaking_news` | boolean | 是否为爆点新闻 |
| `is_suppressed` | boolean | 是否被抑制 |
| `is_downweighted` | boolean | 是否被降权 |

### 监控查询

系统提供了完整的监控查询集合，包括：

1. **抑制效果统计**：统计被抑制和降权的文章数量
2. **抑制前后对比**：分析抑制对分数的影响
3. **话题类型分布**：了解不同类型话题的分布情况
4. **趋势分析**：按时间维度分析抑制效果
5. **数据源分析**：分析不同数据源的抑制效果
6. **质量评估**：评估抑制对内容质量的影响

## 性能优化

### 向量化实现

- 使用pandas的向量化操作替代循环
- 通过布尔掩码实现高效的批量筛选
- 集合操作进行快速的概念匹配

### 内存优化

- 避免创建大量临时对象
- 使用就地修改（in-place modification）
- 合理的数据类型选择

## 部署说明

### 配置 Airflow Variables

在 Airflow UI 中配置必需的变量：

1. 进入 "Admin" → "Variables"
2. 创建或更新上述配置变量
3. 确保 JSON 格式正确

### 验证配置

配置完成后，可以通过以下方式验证：

1. 检查 Airflow Variables 是否正确设置
2. 运行 DAG 查看日志中的抑制效果
3. 查询数据库中的监控字段

## 效果预期

### 短期效果

- 减少常规话题的重复报道
- 降低非核心领域新闻的权重
- 提高核心领域新闻的曝光度

### 长期效果

- 提升选题聚焦度
- 改善用户体验
- 增强系统智能化水平

## 总结

双重话题抑制功能通过智能的向量化算法实现了高效的新闻筛选，在保证性能的同时显著提升了选题质量。该功能为 Phoenix 系统构建了一个逻辑严密、性能卓越且易于监控的"编辑大脑"，使其产出的选题聚焦度达到新的高度。 