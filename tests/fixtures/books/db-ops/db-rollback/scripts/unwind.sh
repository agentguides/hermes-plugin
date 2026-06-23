#!/usr/bin/env bash
# Placeholder for the rollback procedure.
set -euo pipefail
mode="run"
for arg in "$@"; do
  case "$arg" in
    --verify) mode="verify" ;;
  esac
done
if [[ "$mode" == "verify" ]]; then
  echo "[db-rollback/unwind --verify] would: pg_isready && pg_stat_replication=streaming"
  exit 0
fi
echo "[db-rollback/unwind] would: stop pg; swap PGDATA; start pg; reattach replicas"
exit 0
