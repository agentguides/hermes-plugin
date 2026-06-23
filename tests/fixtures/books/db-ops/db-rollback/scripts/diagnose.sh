#!/usr/bin/env bash
# Placeholder for diagnosing a failed restore.
set -euo pipefail
mode="run"
for arg in "$@"; do
  case "$arg" in
    --verify) mode="verify" ;;
  esac
done
if [[ "$mode" == "verify" ]]; then
  printf '{"cause":"disk_space","free_mb":1024,"required_mb":4096}\n'
  exit 0
fi
echo "[db-rollback/diagnose] would capture: pgbackrest info, df -h, log tail"
exit 0
