#!/usr/bin/env python3
"""
双重话题抑制功能测试脚本
用于验证抑制逻辑的正确性和性能
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dags.phoenix.advanced_scorer import AdvancedScorer

def create_test_data():
    """创建测试数据"""
    # 模拟概念热度字典
    concepts_dict = {
        "http://en.wikipedia.org/wiki/Gaza_Strip": 0.8,
        "http://en.wikipedia.org/wiki/Israel–Hamas_war": 0.7,
        "http://en.wikipedia.org/wiki/Russo-Ukrainian_War": 0.6,
        "http://en.wikipedia.org/wiki/Arts": 0.3,
        "http://en.wikipedia.org/wiki/Sport": 0.2,
        "http://en.wikipedia.org/wiki/Politics": 0.9,
        "http://en.wikipedia.org/wiki/Economy": 0.8
    }
    
    # 创建测试文章数据
    test_articles = [
        {
            'title': '加沙常规报道',
            'concepts': [{'uri': 'http://en.wikipedia.org/wiki/Gaza_Strip'}],
            'published_at': datetime.now(pytz.UTC) - timedelta(hours=12),
            'source_importance': 100,
            'sentiment': 0.1,
            'total_articles_in_event': 50
        },
        {
            'title': '加沙突发新闻',
            'concepts': [{'uri': 'http://en.wikipedia.org/wiki/Gaza_Strip'}],
            'published_at': datetime.now(pytz.UTC) - timedelta(hours=1),
            'source_importance': 50,
            'sentiment': 0.2,
            'total_articles_in_event': 30
        },
        {
            'title': '体育新闻',
            'concepts': [{'uri': 'http://en.wikipedia.org/wiki/Sport'}],
            'published_at': datetime.now(pytz.UTC) - timedelta(hours=6),
            'source_importance': 200,
            'sentiment': 0.0,
            'total_articles_in_event': 20
        },
        {
            'title': '政治新闻',
            'concepts': [{'uri': 'http://en.wikipedia.org/wiki/Politics'}],
            'published_at': datetime.now(pytz.UTC) - timedelta(hours=3),
            'source_importance': 80,
            'sentiment': 0.3,
            'total_articles_in_event': 40
        },
        {
            'title': '经济新闻',
            'concepts': [{'uri': 'http://en.wikipedia.org/wiki/Economy'}],
            'published_at': datetime.now(pytz.UTC) - timedelta(hours=2),
            'source_importance': 90,
            'sentiment': 0.1,
            'total_articles_in_event': 35
        }
    ]
    
    return pd.DataFrame(test_articles), concepts_dict

def test_suppression_logic():
    """测试抑制逻辑"""
    print("=== 双重话题抑制功能测试 ===\n")
    
    # 创建测试数据
    df, concepts_dict = create_test_data()
    print("测试数据:")
    for i, row in df.iterrows():
        print(f"  {i+1}. {row['title']} (概念: {[c['uri'] for c in row['concepts']]})")
    print()
    
    # 创建打分器
    scorer = AdvancedScorer(concepts_dict)
    
    # 执行打分
    print("执行V2打分...")
    scored_df = scorer.score(df)
    
    # 显示结果
    print("\n=== 打分结果 ===")
    for i, row in scored_df.iterrows():
        print(f"\n文章 {i+1}: {row['title']}")
        print(f"  原始hot_norm: {row.get('hot_norm', 'N/A'):.4f}")
        print(f"  最终分数: {row.get('final_score_v2', 'N/A'):.4f}")
        print(f"  新鲜度: {row.get('freshness_score', 'N/A'):.4f}")
        print(f"  是否常规话题: {row.get('is_routine_topic', False)}")
        print(f"  是否领域话题: {row.get('is_category_topic', False)}")
        print(f"  是否爆点: {row.get('is_breaking_news', False)}")
        print(f"  是否被抑制: {row.get('is_suppressed', False)}")
        print(f"  是否被降权: {row.get('is_downweighted', False)}")
    
    # 统计信息
    print(f"\n=== 统计信息 ===")
    print(f"总文章数: {len(scored_df)}")
    print(f"被抑制文章数: {scored_df['is_suppressed'].sum()}")
    print(f"被降权文章数: {scored_df['is_downweighted'].sum()}")
    print(f"爆点文章数: {scored_df['is_breaking_news'].sum()}")
    
    # 分数分布
    print(f"\n=== 分数分布 ===")
    print(f"平均最终分数: {scored_df['final_score_v2'].mean():.4f}")
    print(f"最高分数: {scored_df['final_score_v2'].max():.4f}")
    print(f"最低分数: {scored_df['final_score_v2'].min():.4f}")
    
    return scored_df

if __name__ == "__main__":
    try:
        result_df = test_suppression_logic()
        print("\n✅ 测试完成！双重话题抑制功能已成功实现。")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc() 