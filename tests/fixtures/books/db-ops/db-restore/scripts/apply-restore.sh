#!/usr/bin/env bash
# Placeholder for `pgbackrest --stanza=main restore --set=<id>`
set -euo pipefail
mode="run"
for arg in "$@"; do
  case "$arg" in
    --verify) mode="verify" ;;
    --abort)  mode="abort" ;;
  esac
done
case "$mode" in
  verify)
    echo "[db-restore/apply-restore --verify] would check pg_controldata matches label"
    exit 0
    ;;
  abort)
    echo "[db-restore/apply-restore --abort] would stop in-progress restore"
    exit 0
    ;;
  *)
    echo "[db-restore/apply-restore] would: pgbackrest --stanza=main restore --set=<id>"
    exit 0
    ;;
esac
