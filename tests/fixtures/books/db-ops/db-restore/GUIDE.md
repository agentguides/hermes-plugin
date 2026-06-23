---
guide:
  id: db-restore
  version: "0.1.0"
  summary: |
    Restore a Postgres database from a pgBackRest backup. Two steps: pick a
    backup label, apply the restore. On failure of the apply step, delegates
    to the sibling `db-rollback` Guide to undo partial state.
  goal_state: |
    Database restored to the chosen backup label. Replication caught up.
    Application health checks green.
  rollback_strategy: best-effort
  estimated_duration_minutes: 30
  tags: [database, postgres, restore, destructive]
---

# When to use this Guide

You need to restore a Postgres cluster to a known good backup. Either an explicit recovery scenario or rolling back from a botched migration.

# When NOT to use this Guide

- For point-in-time recovery (PITR) inside the WAL window — use `pgbackrest restore --type=time` directly, this Guide doesn't model that yet.
- For partial-table restores — not supported by pgBackRest at this layer.

# Decision criteria

If `020-apply-restore` fails (e.g., disk space, wrong backup label, replica misconfigured), the rescue Guide `db-rollback` runs to unwind partial state before pausing for operator decision.
