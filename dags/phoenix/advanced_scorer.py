# 文件路径: dags/phoenix/advanced_scorer.py
"""
AdvancedScorer - V2系统高级打分器
实现方案B中的所有高级打分算法，包括对数缩放、小簇惩罚和情感权重倾斜
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any
from sklearn.preprocessing import MinMaxScaler

log = logging.getLogger(__name__)

class AdvancedScorer:
    """
    V2系统高级打分器
    封装方案B中提出的所有高级打分算法
    """
    
    def __init__(self, concepts_dict: Dict[str, float]):
        """
        初始化打分器
        
        Args:
            concepts_dict: 概念热度字典，格式为 {uri: score}
        """
        self.concepts_dict = concepts_dict or {}
        log.info(f"AdvancedScorer initialized with {len(self.concepts_dict)} trending concepts")
    
    def _calculate_entity_hot_score(self, concepts_list) -> float:
        """
        计算实体热度分：一篇文章的实体热度，等于它所关联的所有概念中，热度分数最高的那个
        
        Args:
            concepts_list: 文章的概念列表
            
        Returns:
            float: 最高的概念热度分数
        """
        if not concepts_list or not isinstance(concepts_list, list):
            return 0.0
        
        max_score = 0.0
        for concept in concepts_list:
            if isinstance(concept, dict) and 'uri' in concept:
                uri = concept['uri']
                score = self.concepts_dict.get(uri, 0.0)
                max_score = max(max_score, score)
        
        return max_score
    
    def score(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        对输入的DataFrame进行V2打分
        
        Args:
            df: 包含文章数据的DataFrame
            
        Returns:
            pd.DataFrame: 添加了所有V2分数列的DataFrame
        """
        if df.empty:
            log.warning("输入的DataFrame为空，无需打分")
            return df
        
        log.info(f"开始对 {len(df)} 篇文章进行V2打分...")
        
        # 创建DataFrame副本以避免修改原数据
        scored_df = df.copy()
        
        # 1. 计算 entity_hot_score (实体热度分)
        log.info("计算实体热度分 (entity_hot_score)...")
        scored_df['entity_hot_score'] = scored_df['concepts'].apply(
            lambda x: self._calculate_entity_hot_score(x)
        )
        
        # 2. 计算 hot_score_v2 (综合热度分)
        log.info("计算综合热度分 (hot_score_v2)...")
        # 确保total_articles_in_event列存在且为数值，并转换为float
        scored_df['total_articles_in_event'] = pd.to_numeric(
            scored_df['total_articles_in_event'], errors='coerce'
        ).fillna(1).astype(float)
        
        # 确保entity_hot_score为float类型
        scored_df['entity_hot_score'] = pd.to_numeric(
            scored_df['entity_hot_score'], errors='coerce'
        ).fillna(0).astype(float)
        
        scored_df['hot_score_v2'] = (
            np.log1p(scored_df['total_articles_in_event']) + 
            (0.3 * np.log1p(scored_df['entity_hot_score']))
        )
        
        # 3. 计算 rep_score_v2 (代表性分)
        log.info("计算代表性分 (rep_score_v2)...")
        # 为了演示，我们设置默认的cluster_size和centroid_sim值
        # 在实际的聚类系统中，这些值应该来自聚类算法
        if 'cluster_size' not in scored_df.columns:
            scored_df['cluster_size'] = 10  # 默认簇大小
        if 'centroid_sim' not in scored_df.columns:
            scored_df['centroid_sim'] = 0.8  # 默认相似度
        
        # 确保cluster_size列存在且数值大于0，避免log10(0)错误，并转换为float
        scored_df['cluster_size'] = pd.to_numeric(
            scored_df['cluster_size'], errors='coerce'
        ).fillna(1).clip(lower=1).astype(float)
        
        scored_df['centroid_sim'] = pd.to_numeric(
            scored_df['centroid_sim'], errors='coerce'
        ).fillna(1.0).astype(float)
        
        scored_df['rep_score_v2'] = (
            scored_df['centroid_sim'] * 
            (1 - 0.4 * np.log10(scored_df['cluster_size']))
        )
        
        # 4. 计算 sent_score_v2 (情感分)
        log.info("计算情感分 (sent_score_v2)...")
        scored_df['sentiment'] = pd.to_numeric(
            scored_df['sentiment'], errors='coerce'
        ).fillna(0).astype(float)
        
        scored_df['sent_score_v2'] = (
            scored_df['sentiment'].abs() * 
            np.where(scored_df['sentiment'] < 0, 1.25, 1.0)
        )
        
        # 5. 归一化所有分数
        log.info("对所有分数进行归一化...")
        score_columns = ['hot_score_v2', 'rep_score_v2', 'sent_score_v2']
        
        # 调试：检查分数列是否存在
        log.info(f"当前DataFrame列: {list(scored_df.columns)}")
        
        for col in score_columns:
            if col not in scored_df.columns:
                log.error(f"缺少分数列: {col}")
                continue
                
            # 正确的归一化列名：hot_score_v2 -> hot_norm, rep_score_v2 -> rep_norm, sent_score_v2 -> sent_norm
            if col == 'hot_score_v2':
                norm_col = 'hot_norm'
            elif col == 'rep_score_v2':
                norm_col = 'rep_norm'
            elif col == 'sent_score_v2':
                norm_col = 'sent_norm'
            else:
                norm_col = col.replace('_v2', '_norm')
                
            log.info(f"正在归一化 {col} -> {norm_col}")
            
            # 检查列的数据类型和统计信息
            log.info(f"{col} 统计: min={scored_df[col].min():.4f}, max={scored_df[col].max():.4f}, mean={scored_df[col].mean():.4f}")
            
            normalized_series = self._safe_minmax_normalize(scored_df[col])
            scored_df[norm_col] = normalized_series
            
            # 验证归一化结果
            log.info(f"{norm_col} 创建成功，min={scored_df[norm_col].min():.4f}, max={scored_df[norm_col].max():.4f}")
        
        # 调试：检查归一化后的列
        log.info(f"归一化后DataFrame列: {list(scored_df.columns)}")
        
        # 6. 计算最终综合分数 final_score_v2
        log.info("计算最终综合分数 (final_score_v2)...")
        
        # 安全检查：确保所有归一化列都存在
        required_norm_cols = ['hot_norm', 'rep_norm', 'sent_norm']
        missing_cols = [col for col in required_norm_cols if col not in scored_df.columns]
        
        if missing_cols:
            log.error(f"缺少归一化列: {missing_cols}")
            log.error(f"当前列: {list(scored_df.columns)}")
            raise ValueError(f"缺少必需的归一化列: {missing_cols}")
        
        scored_df['final_score_v2'] = (
            0.4 * scored_df['hot_norm'] + 
            0.3 * scored_df['rep_norm'] + 
            0.3 * scored_df['sent_norm']
        )
        
        log.info(f"✅ V2打分完成！最高分: {scored_df['final_score_v2'].max():.4f}")
        
        return scored_df
    
    def _safe_minmax_normalize(self, series: pd.Series) -> pd.Series:
        """
        安全的MinMax归一化，处理分母为零的边界情况
        
        Args:
            series: 需要归一化的数据序列
            
        Returns:
            pd.Series: 归一化后的数据序列
        """
        if series.empty:
            return series
        
        min_val = series.min()
        max_val = series.max()
        
        # 处理分母为零的情况
        if max_val == min_val:
            log.warning(f"数据序列所有值相同 ({min_val})，归一化结果为0.5")
            return pd.Series([0.5] * len(series), index=series.index)
        
        # 标准MinMax归一化
        return (series - min_val) / (max_val - min_val) 