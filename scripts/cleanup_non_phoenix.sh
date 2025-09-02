#!/usr/bin/env bash
set -euo pipefail

# 清理非 Phoenix 代码与资产。默认 dry-run
# 用法：
#   ./scripts/cleanup_non_phoenix.sh --dry-run   # 预览
#   ./scripts/cleanup_non_phoenix.sh --execute   # 执行删除

MODE="--dry-run"
if [[ "${1:-}" == "--execute" ]]; then
  MODE="--execute"
fi

ROOT_DIR="/Users/songyuhang/Desktop/Work/Jiuwanli/dev"
cd "$ROOT_DIR"

# 统一的删除函数（支持 dry-run）
rm_item() {
  local path="$1"
  if [[ $MODE == "--dry-run" ]]; then
    if [[ -e "$path" ]]; then
      echo "[DRY-RUN] WOULD DELETE: $path"
    else
      echo "[SKIP] NOT FOUND: $path" >&2
    fi
  else
    if [[ -e "$path" ]]; then
      echo "[DELETE] $path"
      rm -rf -- "$path"
    else
      echo "[SKIP] NOT FOUND: $path" >&2
    fi
  fi
}

# 1) 备份/V1系统（整目录）
rm_item "$ROOT_DIR/backup/v1_system_20250804"

# 2) 顶层 pipeline 目录（整目录）
rm_item "$ROOT_DIR/pipeline"

# 3) scraper 目录中未被 Phoenix DAG 依赖的模块（仅保留 newsapi_client.py）
for f in \
  activity_analyzer.py aljazeera.py apnews.py base_newsapi.py base.py bbc.py \
  bloomberg.py cnn.py config.py exceptions.py ft.py log_aggregator.py metrics.py \
  nytimes.py quota_manager.py reuters.py scmp.py skynews.py summary_utils.py \
  theguardian.py theverge.py twitter_source.py user_cache.py utils.py elpais.py \
; do
  rm_item "$ROOT_DIR/scraper/$f"
done

# 4) 配置与文档（未形成运行时依赖或已过时）
rm_item "$ROOT_DIR/config/settings.py"
rm_item "$ROOT_DIR/config/quota_config.yaml"

# 5) 旧/辅助 SQL
for f in \
  create_raw_events.sql create_daily_cards.sql create_twitter_users.sql \
  create_summaries.sql create_phoenix_tables.sql \
; do
  rm_item "$ROOT_DIR/sql/$f"
done

# 6) 脚本（测试/一次性/运维辅助）
for f in \
  convert_historical_timestamps.py convert_phoenix_timestamps.py deep_diagnosis_eventregistry.py \
  monitor_eventregistry_quota.py monitor_quota.py validate_api_response.py verify_production_suppression.py \
  verify_rank.py test_eventregistry_auth.py test_fix.py test_key_rotation.py test_lambda_key_rotation.py \
  test_login_error_handling.py test_phoenix_client.py test_simple_key_rotation.py test_topic_suppression.py \
  simple_test.py \
; do
  rm_item "$ROOT_DIR/scripts/$f"
done

# 7) 其它
for f in \
  utils/module_guard.py utils/text.py monitoring_queries.sql \
; do
  rm_item "$ROOT_DIR/$f"
done

# 8) dags/pipeline 旧目录（若仍存在，清理）
rm_item "$ROOT_DIR/dags/pipeline"

# 9) 说明：只做列举，不删除 docs/ 下文档；如需清理，可单独决定
# 可选：如需清理日志聚合相关文档
# rm_item "$ROOT_DIR/docs/log_aggregation.md"
# rm_item "$ROOT_DIR/docs/summary_logs_etl.md"
# rm_item "$ROOT_DIR/docs/twitter_optimization.md"
# rm_item "$ROOT_DIR/docs/quota_management_guide.md"

# 输出总结
if [[ $MODE == "--dry-run" ]]; then
  echo "\nDRY-RUN 完成：以上为将被删除的条目预览。"
else
  echo "\n执行完成：以上条目已被删除。"
fi
