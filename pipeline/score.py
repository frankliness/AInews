"""
量化打分模块
实现基于热度、代表性、情感的量化打分功能
"""
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional
from sqlalchemy import create_engine, text
import os
import sys
import pathlib
from datetime import datetime, timezone

# 添加项目根目录到路径
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from utils.text import minmax

log = logging.getLogger(__name__)

class NewsScorer:
    """新闻打分器"""
    
    def __init__(self, db_url: str, config_path: str = "config.yaml"):
        """
        初始化打分器
        
        Args:
            db_url: 数据库连接URL
            config_path: 配置文件路径
        """
        self.engine = create_engine(db_url)
        self.config = self._load_config(config_path)
        self.beta = self.config.get("coef_hot", {})
        self.weights = self.config.get("mix_weight", {})
        self.tau_hours = self.config.get("decay_tau_hours", 6)
        
    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        try:
            import ruamel.yaml as ryaml
            with open(config_path, 'r', encoding='utf-8') as f:
                return ryaml.YAML().load(f)
        except Exception as e:
            log.warning(f"加载配置文件失败: {e}，使用默认配置")
            return {
                "coef_hot": {"article": 3.0, "src_imp": 1.5, "wgt": 1.0, "likes": 1.0, "rts": 2.0},
                "mix_weight": {"hot": 0.55, "rep": 0.25, "sent": 0.20},
                "decay_tau_hours": 6
            }
    
    def run(self) -> Dict[str, int]:
        """
        执行打分任务
        
        Returns:
            Dict[str, int]: 打分统计信息
        """
        log.info("🚀 开始新闻打分...")
        
        # 1. 获取24小时内的数据
        df = self._fetch_recent_data()
        if df.empty:
            log.warning("没有找到24小时内的数据")
            return {"total_records": 0, "scored_records": 0}
        
        log.info(f"📊 获取到 {len(df)} 条记录")
        
        # 2. 计算各项分数
        df = self._calculate_scores(df)
        
        # 3. 更新数据库
        stats = self._update_database(df)
        
        log.info(f"✅ 打分完成: {stats}")
        return stats
    
    def _fetch_recent_data(self) -> pd.DataFrame:
        """获取24小时内的数据"""
        query = """
            SELECT id, title, body, published_at, url, likes, retweets,
                   total_articles_24h, source_importance, wgt, centroid_sim,
                   sentiment, topic_id, cluster_size
            FROM raw_events
            WHERE published_at >= NOW() - INTERVAL '24 HOURS'
        """
        
        try:
            df = pd.read_sql(query, self.engine)
            return df
        except Exception as e:
            log.error(f"获取数据失败: {e}")
            return pd.DataFrame()
    
    def _calculate_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算各项分数"""
        log.info("🔢 计算各项分数...")
        
        now = pd.Timestamp.now(timezone.utc)
        
        # 1. 计算热度分数
        df = self._calculate_hot_score(df, now)
        
        # 2. 计算代表性分数
        df = self._calculate_rep_score(df)
        
        # 3. 计算情感分数
        df = self._calculate_sent_score(df)
        
        # 4. 计算综合分数
        df = self._calculate_final_score(df)
        
        return df
    
    def _calculate_hot_score(self, df: pd.DataFrame, now: pd.Timestamp) -> pd.DataFrame:
        """计算热度分数"""
        # 填充缺失值
        df["total_articles_24h"] = df["total_articles_24h"].fillna(0)
        df["source_importance"] = df["source_importance"].fillna(1)
        df["wgt"] = df["wgt"].fillna(1)
        df["likes"] = df["likes"].fillna(0)
        df["retweets"] = df["retweets"].fillna(0)
        
        # 计算原始热度分数
        df["hot_raw"] = (
            self.beta.get("article", 3.0) * df["total_articles_24h"] +
            self.beta.get("src_imp", 1.5) * df["source_importance"] +
            self.beta.get("wgt", 1.0) * df["wgt"] +
            self.beta.get("likes", 1.0) * df["likes"] +
            self.beta.get("rts", 2.0) * df["retweets"]
        )
        
        # 时间衰减
        time_diff = (now - df["published_at"]).dt.total_seconds() / 3600  # 转换为小时
        decay_factor = np.exp(-time_diff / self.tau_hours)
        df["hot_norm"] = minmax(df["hot_raw"] * decay_factor)
        
        log.info(f"📈 热度分数计算完成，范围: {df['hot_norm'].min():.3f} - {df['hot_norm'].max():.3f}")
        return df
    
    def _calculate_rep_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算代表性分数"""
        # 使用centroid_sim作为代表性分数
        df["centroid_sim"] = df["centroid_sim"].fillna(0.5)
        df["rep_norm"] = minmax(df["centroid_sim"])
        
        log.info(f"🎯 代表性分数计算完成，范围: {df['rep_norm'].min():.3f} - {df['rep_norm'].max():.3f}")
        return df
    
    def _calculate_sent_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算情感分数"""
        # 使用情感分析分数
        df["sentiment"] = df["sentiment"].fillna(0)
        df["sent_norm"] = minmax(df["sentiment"].abs())  # 使用绝对值
        
        log.info(f"😊 情感分数计算完成，范围: {df['sent_norm'].min():.3f} - {df['sent_norm'].max():.3f}")
        return df
    
    def _calculate_final_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算综合分数"""
        df["score"] = (
            self.weights.get("hot", 0.55) * df["hot_norm"] +
            self.weights.get("rep", 0.25) * df["rep_norm"] +
            self.weights.get("sent", 0.20) * df["sent_norm"]
        )
        
        # 归一化到[0, 1]
        df["score"] = minmax(df["score"])
        
        log.info(f"🏆 综合分数计算完成，范围: {df['score'].min():.3f} - {df['score'].max():.3f}")
        return df
    
    def _update_database(self, df: pd.DataFrame) -> Dict[str, int]:
        """更新数据库"""
        log.info("💾 更新数据库...")
        
        # 准备更新数据
        update_data = df[["id", "hot_raw", "hot_norm", "rep_norm", "sent_norm", "score"]].copy()
        
        # 写入临时表
        update_data.to_sql("tmp_score", self.engine, if_exists="replace", index=False)
        
        # 执行更新
        with self.engine.begin() as conn:
            result = conn.execute(text("""
                UPDATE raw_events r
                SET hot_raw    = t.hot_raw,
                    hot_norm   = t.hot_norm,
                    rep_norm   = t.rep_norm,
                    sent_norm  = t.sent_norm,
                    score      = t.score
                FROM tmp_score t 
                WHERE r.id = t.id
            """))
            
            # 删除临时表
            conn.execute(text("DROP TABLE IF EXISTS tmp_score"))
            
            updated_count = result.rowcount
        
        # 统计高分记录
        high_score_count = len(df[df["score"] >= 0.6])
        
        stats = {
            "total_records": len(df),
            "scored_records": updated_count,
            "high_score_records": high_score_count,
            "avg_score": df["score"].mean()
        }
        
        log.info(f"✅ 数据库更新完成: {stats}")
        return stats

def run():
    """运行打分任务"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("❌ DATABASE_URL 尚未设置！")
    
    scorer = NewsScorer(db_url)
    return scorer.run()

if __name__ == "__main__":
    run() 