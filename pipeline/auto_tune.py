"""
自动调参模块
实现基于历史数据的参数自动优化功能
"""
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple
from sqlalchemy import create_engine, text
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import os
import sys
import pathlib
from datetime import datetime, timedelta

# 添加项目根目录到路径
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

log = logging.getLogger(__name__)

class AutoTuner:
    """自动调参器"""
    
    def __init__(self, db_url: str, config_path: str = "config.yaml"):
        """
        初始化自动调参器
        
        Args:
            db_url: 数据库连接URL
            config_path: 配置文件路径
        """
        self.engine = create_engine(db_url)
        self.config_path = config_path
        self.scaler = StandardScaler()
        
    def run(self) -> Dict[str, float]:
        """
        执行自动调参任务
        
        Returns:
            Dict[str, float]: 调参结果统计
        """
        log.info("🚀 开始自动调参...")
        
        # 1. 获取历史数据
        df = self._fetch_historical_data()
        if df.empty:
            log.warning("没有找到足够的历史数据")
            return {"status": "no_data"}
        
        log.info(f"📊 获取到 {len(df)} 条历史记录")
        
        # 2. 准备训练数据
        X, y = self._prepare_training_data(df)
        
        # 3. 训练模型
        model = self._train_model(X, y)
        
        # 4. 提取新参数
        new_params = self._extract_parameters(model, X)
        
        # 5. 更新配置文件
        stats = self._update_config(new_params)
        
        log.info(f"✅ 自动调参完成: {stats}")
        return stats
    
    def _fetch_historical_data(self) -> pd.DataFrame:
        """获取过去7天的历史数据"""
        query = """
            SELECT r.id, r.title, r.body, r.published_at, r.url,
                   r.total_articles_24h, r.source_importance, r.wgt,
                   r.likes, r.retweets, r.centroid_sim, r.sentiment,
                   r.score, r.topic_id, r.cluster_size,
                   CASE WHEN d.id IS NOT NULL THEN 1 ELSE 0 END as selected
            FROM raw_events r
            LEFT JOIN daily_cards d ON r.id = d.raw_id
            WHERE r.published_at >= NOW() - INTERVAL '7 DAYS'
              AND r.score IS NOT NULL
        """
        
        try:
            df = pd.read_sql(query, self.engine)
            return df
        except Exception as e:
            log.error(f"获取历史数据失败: {e}")
            return pd.DataFrame()
    
    def _prepare_training_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """准备训练数据"""
        log.info("🔧 准备训练数据...")
        
        # 特征列
        feature_columns = [
            'total_articles_24h', 'source_importance', 'wgt',
            'likes', 'retweets', 'centroid_sim', 'sentiment'
        ]
        
        # 填充缺失值
        for col in feature_columns:
            if col in ['likes', 'retweets', 'total_articles_24h']:
                df[col] = df[col].fillna(0)
            elif col == 'sentiment':
                df[col] = df[col].fillna(0)
            else:
                df[col] = df[col].fillna(1)
        
        # 准备特征矩阵
        X = df[feature_columns].values
        y = df['selected'].values
        
        # 标准化特征
        X_scaled = self.scaler.fit_transform(X)
        
        log.info(f"📈 训练数据准备完成: {X_scaled.shape[0]} 样本, {X_scaled.shape[1]} 特征")
        log.info(f"🎯 正样本比例: {y.mean():.2%}")
        
        return X_scaled, y
    
    def _train_model(self, X: np.ndarray, y: np.ndarray) -> LogisticRegression:
        """训练逻辑回归模型"""
        log.info("🤖 训练逻辑回归模型...")
        
        # 使用LogisticRegression，设置positive=True确保正样本权重
        model = LogisticRegression(
            C=0.01,  # 正则化强度
            max_iter=1000,
            random_state=42,
            class_weight='balanced'  # 处理类别不平衡
        )
        
        model.fit(X, y)
        
        # 评估模型
        train_score = model.score(X, y)
        log.info(f"📊 模型训练完成，准确率: {train_score:.3f}")
        
        return model
    
    def _extract_parameters(self, model: LogisticRegression, X: np.ndarray) -> Dict[str, float]:
        """从模型系数中提取新参数"""
        log.info("🔍 提取新参数...")
        
        # 获取特征重要性（系数绝对值）
        feature_importance = np.abs(model.coef_[0])
        
        # 反标准化系数
        feature_importance_original = feature_importance / self.scaler.scale_
        
        # 映射到配置参数
        new_params = {
            "coef_hot": {
                "article": float(feature_importance_original[0]),  # total_articles_24h
                "src_imp": float(feature_importance_original[1]),  # source_importance
                "wgt": float(feature_importance_original[2]),      # wgt
                "likes": float(feature_importance_original[3]),    # likes
                "rts": float(feature_importance_original[4])       # retweets
            },
            "mix_weight": {
                "hot": 0.55,    # 保持固定
                "rep": 0.25,    # 保持固定
                "sent": 0.20    # 保持固定
            }
        }
        
        # 归一化热度系数
        hot_coefs = list(new_params["coef_hot"].values())
        total_hot = sum(hot_coefs)
        if total_hot > 0:
            for key in new_params["coef_hot"]:
                new_params["coef_hot"][key] = new_params["coef_hot"][key] / total_hot * 10  # 缩放到合理范围
        
        log.info(f"📊 新参数提取完成: {new_params}")
        return new_params
    
    def _update_config(self, new_params: Dict[str, Dict]) -> Dict[str, float]:
        """更新配置文件"""
        log.info("💾 更新配置文件...")
        
        try:
            import ruamel.yaml as ryaml
            
            # 读取现有配置
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = ryaml.YAML().load(f)
            
            # 更新参数
            config["coef_hot"] = new_params["coef_hot"]
            config["mix_weight"] = new_params["mix_weight"]
            
            # 添加调参时间戳
            config["last_tune_time"] = datetime.now().isoformat()
            
            # 写回配置文件
            with open(self.config_path, 'w', encoding='utf-8') as f:
                ryaml.YAML().dump(config, f)
            
            stats = {
                "status": "success",
                "updated_coef_hot": new_params["coef_hot"],
                "updated_mix_weight": new_params["mix_weight"],
                "tune_time": datetime.now().isoformat()
            }
            
            log.info(f"✅ 配置文件更新完成")
            return stats
            
        except Exception as e:
            log.error(f"更新配置文件失败: {e}")
            return {"status": "error", "message": str(e)}

def run():
    """运行自动调参任务"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("❌ DATABASE_URL 尚未设置！")
    
    tuner = AutoTuner(db_url)
    return tuner.run()

if __name__ == "__main__":
    run() 