#!/usr/bin/env bash
# Placeholder for `pgbackrest --stanza=main backup --type=full`.
set -euo pipefail
mode="run"
for arg in "$@"; do
  case "$arg" in
    --verify) mode="verify" ;;
  esac
done
if [[ "$mode" == "verify" ]]; then
  printf '{"snapshot_id":"snap-%s","timestamp":"%s","stanza":"main"}\n' \
    "$(date -u +%s)" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  exit 0
fi
echo "[db-backup/snapshot] would: pgbackrest --stanza=main backup --type=full"
exit 0
