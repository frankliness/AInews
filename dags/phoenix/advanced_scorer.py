# 文件路径: dags/phoenix/advanced_scorer.py
"""
AdvancedScorer - V2系统高级打分器
实现方案B中的所有高级打分算法，包括对数缩放、小簇惩罚和情感权重倾斜
"""

import logging
import math
from datetime import datetime
import pytz
import numpy as np
import pandas as pd
from typing import Dict, Any
from sklearn.preprocessing import MinMaxScaler
from airflow.models import Variable

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
        
        # 第一步：读取所有评分参数
        log.info("从Airflow Variables读取评分参数...")
        # 读取新鲜度计算参数
        tau = float(Variable.get("ainews_freshness_tau_hours", default_var=6))
        
        # 读取所有维度的权重
        w_hot = float(Variable.get("ainews_weight_hot", default_var=0.35))
        w_auth = float(Variable.get("ainews_weight_authority", default_var=0.25))
        w_concept = float(Variable.get("ainews_weight_concept", default_var=0.20))
        w_fresh = float(Variable.get("ainews_weight_freshness", default_var=0.15))
        w_sent = float(Variable.get("ainews_weight_sentiment", default_var=0.05))
        
        log.info(f"评分参数: tau={tau}, w_hot={w_hot}, w_auth={w_auth}, w_concept={w_concept}, w_fresh={w_fresh}, w_sent={w_sent}")
        
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
        
        # 3. 计算权威分 (rep_score_v2) - 使用从API获取的importanceRank
        log.info("计算权威分 (rep_score_v2)...")
        
        # --- 开始计算权威分 ---
        log.info("Calculating authority score from API-fetched source_importance (rank)...")

        # 1. 反转排名：排名越低（数字越大），分数越低。我们将其转换为 0-1 的分数。
        #    我们知道 importanceRank 数字越小越好。
        #    公式: score = (基数 - rank) / 基数
        #    我们使用 .fillna() 处理空值，给予一个非常靠后的默认排名 (1,000,001)，使其得分接近于0。
        scored_df['rep_norm'] = (1000001 - scored_df['source_importance'].fillna(1000001)) / 1000000.0

        # 2. 将分数限制在 [0, 1] 区间内，防止因异常rank值导致分数超出范围。
        scored_df['rep_norm'] = scored_df['rep_norm'].clip(lower=0, upper=1)

        log.info("Authority score calculation complete.")
        # --- 结束计算权威分 ---
        
        # 为了保持兼容性，我们也将rep_norm赋值给rep_score_v2
        scored_df['rep_score_v2'] = scored_df['rep_norm']
        
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
        score_columns = ['hot_score_v2', 'sent_score_v2', 'entity_hot_score']  # 移除 rep_score_v2，因为我们已经直接计算了 rep_norm
        
        # 调试：检查分数列是否存在
        log.info(f"当前DataFrame列: {list(scored_df.columns)}")
        
        for col in score_columns:
            if col not in scored_df.columns:
                log.error(f"缺少分数列: {col}")
                continue
                
            # 正确的归一化列名：hot_score_v2 -> hot_norm, sent_score_v2 -> sent_norm, entity_hot_score -> concept_hot_norm
            if col == 'hot_score_v2':
                norm_col = 'hot_norm'
            elif col == 'sent_score_v2':
                norm_col = 'sent_norm'
            elif col == 'entity_hot_score':
                norm_col = 'concept_hot_norm'
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
        
        # 第二步：计算时区感知的"新鲜分"
        log.info("Calculating timezone-aware freshness score...")
        beijing_tz = pytz.timezone('Asia/Shanghai')
        utc_now = datetime.now(pytz.utc)

        # 确保 'published_at' 列是 pandas 的 datetime 类型
        scored_df['published_at'] = pd.to_datetime(scored_df['published_at'])

        # 处理时区转换 - 检查是否已经是时区感知的
        if scored_df['published_at'].dt.tz is None:
            # 如果还没有时区信息，假设是北京时间并添加时区信息
            published_at_beijing = scored_df['published_at'].dt.tz_localize(beijing_tz)
        else:
            # 如果已经有时区信息，直接使用
            published_at_beijing = scored_df['published_at']

        # 转换为标准的 UTC 时间
        published_at_utc = published_at_beijing.dt.tz_convert(pytz.utc)

        # 计算与当前 UTC 时间的差值（单位：小时）
        time_diff = utc_now - published_at_utc
        hours_diff = time_diff.dt.total_seconds() / 3600

        # 应用指数衰减公式计算新鲜分
        scored_df['freshness_score'] = np.exp(-hours_diff / tau)
        log.info("Freshness score calculation complete.")
        
        # 第三步：更新最终总分计算公式
        log.info("计算最终综合分数 (final_score_v2)...")
        
        # 安全检查：确保所有归一化列都存在
        required_norm_cols = ['hot_norm', 'rep_norm', 'sent_norm', 'concept_hot_norm']  # rep_norm 已经通过权威分计算直接生成
        missing_cols = [col for col in required_norm_cols if col not in scored_df.columns]
        
        if missing_cols:
            log.error(f"缺少归一化列: {missing_cols}")
            log.error(f"当前列: {list(scored_df.columns)}")
            raise ValueError(f"缺少必需的归一化列: {missing_cols}")
        
        # 更新最终总分公式，加入新鲜分并使用从Airflow读取的权重
        scored_df['final_score_v2'] = (
            scored_df['hot_norm'] * w_hot +
            scored_df['rep_norm'] * w_auth +       # 假设 rep_norm 代表权威度
            scored_df['concept_hot_norm'] * w_concept + # 假设 concept_hot_norm 代表概念热度
            scored_df['freshness_score'] * w_fresh +
            scored_df['sent_norm'] * w_sent
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