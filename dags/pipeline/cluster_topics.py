"""
主题聚类模块
实现EventRegistry事件聚类和细分功能
"""
import pandas as pd
import numpy as np
import logging
from typing import List, Dict, Optional
from sqlalchemy import create_engine, text
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler
import os
import sys
import pathlib

# 添加项目根目录到路径
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from utils.text import cosine, parse_embedding

log = logging.getLogger(__name__)

class TopicClusterer:
    """主题聚类器"""
    
    def __init__(self, db_url: str, config_path: str = "config.yaml"):
        """
        初始化聚类器
        
        Args:
            db_url: 数据库连接URL
            config_path: 配置文件路径
        """
        self.engine = create_engine(db_url)
        self.config = self._load_config(config_path)
        self.n_clusters = self.config.get("clustering", {}).get("n_clusters", 150)
        self.max_cluster_size = self.config.get("clustering", {}).get("max_cluster_size", 50)
        
    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        try:
            import ruamel.yaml as ryaml
            with open(config_path, 'r', encoding='utf-8') as f:
                return ryaml.YAML().load(f)
        except Exception as e:
            log.warning(f"加载配置文件失败: {e}，使用默认配置")
            return {}
    
    def run(self) -> Dict[str, int]:
        """
        执行聚类任务
        
        Returns:
            Dict[str, int]: 聚类统计信息
        """
        log.info("🚀 开始主题聚类...")
        
        # 1. 获取24小时内的数据
        df = self._fetch_recent_data()
        if df.empty:
            log.warning("没有找到24小时内的数据")
            return {"total_records": 0, "clustered_records": 0}
        
        log.info(f"📊 获取到 {len(df)} 条记录")
        
        # 2. 一级聚类：使用EventRegistry的event_id
        df = self._primary_clustering(df)
        
        # 3. 二级聚类：对超大事件进行细分
        df = self._secondary_clustering(df)
        
        # 4. 更新数据库
        stats = self._update_database(df)
        
        log.info(f"✅ 聚类完成: {stats}")
        return stats
    
    def _fetch_recent_data(self) -> pd.DataFrame:
        """获取24小时内的数据"""
        query = """
            SELECT id, event_id, embedding, published_at
            FROM raw_events
            WHERE published_at >= NOW() - INTERVAL '24 HOURS'
              AND event_id IS NOT NULL
        """
        
        try:
            df = pd.read_sql(query, self.engine)
            return df
        except Exception as e:
            log.error(f"获取数据失败: {e}")
            return pd.DataFrame()
    
    def _primary_clustering(self, df: pd.DataFrame) -> pd.DataFrame:
        """一级聚类：使用EventRegistry的event_id"""
        log.info("🔍 执行一级聚类...")
        
        # 将event_id转换为数字作为topic_id
        # 使用hash函数将字符串转换为数字
        df["topic_id"] = df["event_id"].apply(lambda x: hash(x) % (2**63 - 1))
        df["centroid_sim"] = 1.0  # 同一事件的相似度为1
        
        # 统计cluster_size
        size_counts = df.groupby("topic_id").size().rename("cluster_size")
        df = df.join(size_counts, on="topic_id")
        
        log.info(f"📈 一级聚类完成，共 {df['topic_id'].nunique()} 个主题")
        return df
    
    def _secondary_clustering(self, df: pd.DataFrame) -> pd.DataFrame:
        """二级聚类：对超大事件进行细分"""
        log.info("🔍 执行二级聚类...")
        
        # 找出超大事件
        big_clusters = df[df.cluster_size > self.max_cluster_size]
        
        if big_clusters.empty:
            log.info("没有超大事件需要细分")
            return df
        
        log.info(f"📊 发现 {len(big_clusters)} 个超大事件，开始细分...")
        
        # 对每个超大事件进行细分
        for topic_id in big_clusters["topic_id"].unique():
            cluster_data = df[df["topic_id"] == topic_id]
            
            # 解析embedding
            embeddings = []
            valid_indices = []
            
            for idx, row in cluster_data.iterrows():
                embedding = parse_embedding(row["embedding"])
                if embedding:
                    embeddings.append(embedding)
                    valid_indices.append(idx)
            
            if len(embeddings) < 3:
                continue  # 跳过太小的聚类
            
            # 执行K-means聚类
            k = min(self.n_clusters // 10, len(embeddings) // 3, 10)  # 限制聚类数
            if k < 2:
                continue
            
            try:
                km = MiniBatchKMeans(n_clusters=k, random_state=42, batch_size=100)
                km.fit(embeddings)
                
                # 更新topic_id和相似度
                for i, idx in enumerate(valid_indices):
                    new_topic_id = f"{topic_id}_sub_{km.labels_[i]}"
                    df.loc[idx, "topic_id"] = new_topic_id
                    
                    # 计算与聚类中心的相似度
                    centroid = km.cluster_centers_[km.labels_[i]]
                    similarity = cosine(embeddings[i], centroid)
                    df.loc[idx, "centroid_sim"] = similarity
                    
            except Exception as e:
                log.error(f"细分聚类 {topic_id} 失败: {e}")
                continue
        
        # 重新计算cluster_size
        size_counts = df.groupby("topic_id").size().rename("cluster_size")
        df = df.drop(columns=["cluster_size"]).join(size_counts, on="topic_id")
        
        log.info(f"✅ 二级聚类完成，细分后共 {df['topic_id'].nunique()} 个主题")
        return df
    
    def _update_database(self, df: pd.DataFrame) -> Dict[str, int]:
        """更新数据库"""
        log.info("💾 更新数据库...")
        
        # 准备更新数据
        update_data = df[["id", "topic_id", "cluster_size", "centroid_sim"]].copy()
        
        # 写入临时表
        update_data.to_sql("tmp_cluster", self.engine, if_exists="replace", index=False)
        
        # 执行更新
        with self.engine.begin() as conn:
            result = conn.execute(text("""
                UPDATE raw_events r
                SET topic_id      = t.topic_id,
                    cluster_size  = t.cluster_size,
                    centroid_sim  = t.centroid_sim
                FROM tmp_cluster t 
                WHERE r.id = t.id
            """))
            
            # 删除临时表
            conn.execute(text("DROP TABLE IF EXISTS tmp_cluster"))
            
            updated_count = result.rowcount
        
        stats = {
            "total_records": len(df),
            "clustered_records": updated_count,
            "unique_topics": df["topic_id"].nunique()
        }
        
        log.info(f"✅ 数据库更新完成: {stats}")
        return stats

def run():
    """运行聚类任务"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("❌ DATABASE_URL 尚未设置！")
    
    clusterer = TopicClusterer(db_url)
    return clusterer.run()

if __name__ == "__main__":
    run() 