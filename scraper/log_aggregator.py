#!/usr/bin/env python3
"""
日志汇总器
将所有新闻和推文抓取日志按日期汇总到统一目录
"""

import os
import json
import glob
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import logging
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


class LogAggregator:
    """日志汇总器"""
    
    def __init__(self, logs_dir: str = "logs/news"):
        self.logs_dir = Path(logs_dir)
        self.summary_dir = self.logs_dir / "summary"
        self.summary_dir.mkdir(exist_ok=True)
        
    def get_all_news_sources(self) -> List[str]:
        """获取所有新闻源目录"""
        sources = []
        for item in self.logs_dir.iterdir():
            if item.is_dir() and item.name != "summary":
                sources.append(item.name)
        return sources
    
    def get_log_files_by_date(self, source: str, target_date: date) -> List[Path]:
        """获取指定日期和源的所有日志文件"""
        source_dir = self.logs_dir / source
        if not source_dir.exists():
            return []
            
        date_str = target_date.strftime("%Y-%m-%d")
        pattern = f"{source}_{date_str}.log"
        log_files = list(source_dir.glob(pattern))
        return log_files
    
    def aggregate_logs_by_date(self, target_date: date) -> list:
        """全局收集所有新闻（带 sentiment 和 url），排序后只保留前100条，返回新闻列表"""
        sources = self.get_all_news_sources()
        all_news_with_sentiment = []
        
        for source in sources:
            log_files = self.get_log_files_by_date(source, target_date)
            for log_file in log_files:
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                log_data = json.loads(line)
                                if 'url' in log_data and log_data['url'] and 'sentiment' in log_data:
                                    log_data['source'] = source  # 加上来源字段
                                    all_news_with_sentiment.append(log_data)
                            except Exception:
                                continue
                except Exception as e:
                    logger.error(f"读取日志文件失败 {log_file}: {e}")
        # 排序并取前100条
        all_news_with_sentiment.sort(key=lambda x: abs(x['sentiment']), reverse=True)
        return all_news_with_sentiment[:100]

    def create_summary_file(self, target_date: date, news_list: list) -> Path:
        """创建全局 top100 格式的汇总文件"""
        date_str = target_date.strftime("%Y-%m-%d")
        summary_file = self.summary_dir / f"summary_{date_str}.log"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"=== 新闻抓取日志汇总 {date_str} ===\n")
            f.write(f"汇总时间: {datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总条数: {len(news_list)}\n\n")
            for i, news in enumerate(news_list, 1):
                f.write(f"[{i}] {json.dumps(news, ensure_ascii=False)}\n")
        return summary_file

    def create_summary_json(self, target_date: date, news_list: list) -> Path:
        """创建全局 top100 格式的 JSON 汇总文件"""
        date_str = target_date.strftime("%Y-%m-%d")
        summary_json = self.summary_dir / f"summary_{date_str}.json"
        summary_data = {
            "date": date_str,
            "aggregated_at": datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
            "total": len(news_list),
            "news": news_list
        }
        with open(summary_json, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)
        return summary_json

    def aggregate_daily_logs(self, target_date: Optional[date] = None) -> dict:
        """汇总指定日期的所有日志文件，输出全局 top100"""
        if target_date is None:
            target_date = date.today()
        logger.info(f"开始汇总 {target_date} 的日志")
        news_list = self.aggregate_logs_by_date(target_date)
        if not news_list:
            logger.warning(f"未找到 {target_date} 的日志文件")
            return {}
        summary_file = self.create_summary_file(target_date, news_list)
        summary_json = self.create_summary_json(target_date, news_list)
        logger.info(f"✅ 汇总完成: {summary_file}")
        logger.info(f"✅ JSON汇总: {summary_json}")
        logger.info(f"  - 总条数: {len(news_list)} 条")
        if news_list:
            logger.info(f"  - 最高sentiment绝对值: {abs(news_list[0]['sentiment'])}")
            logger.info(f"  - 最低sentiment绝对值: {abs(news_list[-1]['sentiment'])}")
        return {
            "log": summary_file,
            "json": summary_json,
            "stats": {
                "total": len(news_list),
                "max_sentiment": abs(news_list[0]['sentiment']) if news_list else None,
                "min_sentiment": abs(news_list[-1]['sentiment']) if news_list else None
            }
        }
    
    def aggregate_recent_logs(self, days: int = 7) -> Dict[str, List[Path]]:
        """汇总最近几天的日志"""
        results = {"log": [], "json": []}
        
        for i in range(days):
            target_date = date.today() - timedelta(days=i)
            try:
                result = self.aggregate_daily_logs(target_date)
                if result:
                    results["log"].append(result["log"])
                    results["json"].append(result["json"])
            except Exception as e:
                logger.error(f"汇总 {target_date} 日志失败: {e}")
        
        return results


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="新闻日志汇总工具")
    parser.add_argument("--date", help="指定日期 (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, default=1, help="汇总最近几天 (默认1天)")
    parser.add_argument("--logs-dir", default="logs/news", help="日志目录")
    
    args = parser.parse_args()
    
    aggregator = LogAggregator(args.logs_dir)
    
    if args.date:
        # 汇总指定日期
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        aggregator.aggregate_daily_logs(target_date)
    else:
        # 汇总最近几天
        aggregator.aggregate_recent_logs(args.days)


if __name__ == "__main__":
    main() 