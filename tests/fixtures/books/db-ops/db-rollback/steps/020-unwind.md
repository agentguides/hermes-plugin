---
step:
  id: unwind
  title: Restore the prior data directory and reattach replicas
  requires: [diagnose]
  performer: agent
  action:
    type: script
    script: scripts/unwind.sh
    timeout_seconds: 600
  verify:
    type: script
    script: scripts/unwind.sh
    args: ["--verify"]
    success_exit: 0
  on_failure:
    strategy: abort
  estimated_duration_minutes: 7
  tags: [destructive, recovery]
---

# What this step does

Stops postgres on the primary, swaps `$PGDATA` back to the pre-restore copy (kept under `$PGDATA.pre-restore`), restarts postgres, and forces replicas to re-establish replication slots.

# Success criteria

- Postgres restarts and accepts queries.
- All declared replicas reach `streaming` state.
