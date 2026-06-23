---
guide:
  id: db-rollback
  version: "0.1.0"
  summary: |
    Roll back a partial pgBackRest restore: stop postgres, swap the data
    directory back to its pre-restore state, restart, reattach replicas.
  goal_state: |
    Primary serving the pre-restore data directory. Replicas reattached and
    streaming. No partial restore artifacts on disk.
  rollback_strategy: none
  estimated_duration_minutes: 10
  tags: [database, postgres, rescue]
---

# When this Guide runs

Invoked automatically when `db-restore`'s `020-apply-restore` step fails. The parent run pauses while this Guide drives the unwind, then resumes for operator decision (per the parent's `resume_after_recovery: false`).
