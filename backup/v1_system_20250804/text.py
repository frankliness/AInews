"""
文本处理工具函数
"""
import numpy as np
import json
from typing import List, Union

def cosine(a: Union[List[float], np.ndarray], b: Union[List[float], np.ndarray]) -> float:
    """
    计算两个向量的余弦相似度
    
    Args:
        a: 向量a
        b: 向量b
    
    Returns:
        float: 余弦相似度 [0, 1]
    """
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

def minmax(s: Union[List[float], np.ndarray]) -> np.ndarray:
    """
    对向量进行min-max归一化
    
    Args:
        s: 输入向量
    
    Returns:
        np.ndarray: 归一化后的向量 [0, 1]
    """
    s = np.array(s)
    min_val = s.min()
    max_val = s.max()
    
    # 检查分母是否为零
    if max_val == min_val:
        # 如果所有值都一样，我们无法区分它们，因此返回一个中立的分数0.5
        # 或者，如果这个序列只有一个值，它本身就应该得到满分1.0或中性分0.5，具体取决于业务逻辑。我们暂时选择0.5。
        return np.full_like(s, 0.5)
    
    return (s - min_val) / (max_val - min_val)

def parse_embedding(embedding_str: str) -> List[float]:
    """
    解析JSON格式的embedding字符串
    
    Args:
        embedding_str: JSON格式的embedding字符串
    
    Returns:
        List[float]: embedding向量
    """
    try:
        return json.loads(embedding_str)
    except (json.JSONDecodeError, TypeError):
        return []

def encode_embedding(embedding: List[float]) -> str:
    """
    将embedding向量编码为JSON字符串
    
    Args:
        embedding: embedding向量
    
    Returns:
        str: JSON格式的字符串
    """
    return json.dumps(embedding) 