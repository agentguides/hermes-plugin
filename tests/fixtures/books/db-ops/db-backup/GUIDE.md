---
guide:
  id: db-backup
  version: "0.1.0"
  summary: |
    Trigger a pgBackRest full backup and verify it landed in the stanza. About
    10 minutes for a small database; longer for larger ones.
  goal_state: |
    A fresh full backup labelled in the pgBackRest stanza, verified via
    `pgbackrest info`. Ready to be used as a restore point.
  rollback_strategy: none
  estimated_duration_minutes: 10
  tags: [database, postgres, backup]
---

# When to use this Guide

You need a fresh backup before a risky operation (migration, schema change, rollout), or you want an ad-hoc restore point on demand.

# When NOT to use this Guide

- Scheduled / continuous backups — those should run via cron or `pgbackrest --type=incr`, not via a Guide.
- WAL archiving setup — that's a one-time configuration, not a per-run workflow.
