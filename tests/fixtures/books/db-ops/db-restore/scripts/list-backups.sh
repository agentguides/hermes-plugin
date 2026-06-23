#!/usr/bin/env bash
# Placeholder for `pgbackrest --stanza=main info --output=json | jq …`
set -euo pipefail
mode="run"
for arg in "$@"; do
  case "$arg" in
    --verify) mode="verify" ;;
  esac
done
if [[ "$mode" == "verify" ]]; then
  printf '{"backup_id":"snap-%s","label":"latest-full","stanza":"main"}\n' "$(date -u +%s)"
  exit 0
fi
echo "[db-restore/pick-backup] would query: pgbackrest --stanza=main info"
exit 0
