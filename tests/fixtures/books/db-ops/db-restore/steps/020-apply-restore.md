---
step:
  id: apply-restore
  title: Apply pgBackRest restore to the primary
  requires: [pick-backup]
  performer: agent
  action:
    type: script
    script: scripts/apply-restore.sh
    timeout_seconds: 3600
  verify:
    type: script
    script: scripts/apply-restore.sh
    args: ["--verify"]
    success_exit: 0
  on_failure:
    strategy: recover
    recover_with: "guide:db-rollback"
    resume_after_recovery: false
    max_retries: 1
  rollback:
    type: script
    script: scripts/apply-restore.sh
  estimated_duration_minutes: 25
  tags: [destructive, point-of-no-return]
---

# What this step does

Calls `pgbackrest --stanza=main restore --set=<backup_id>`. This is the point of no return — once it begins, the primary's data directory is being overwritten.

# Success criteria

- Restore exits 0.
- Verify script reports the data directory matches the chosen backup label.

# What can go wrong

| Failure | Likely cause | Action |
|---|---|---|
| Disk space | New backup is larger than free space | rescue Guide unmounts partial restore; operator frees space |
| Permission denied | postgres user can't write data dir | rescue Guide chowns; or operator fixes manually |
| Replicas refuse to follow | Replication slot mismatch | rescue Guide pauses replication; operator reseeds |

The sibling `guide:db-rollback` Guide handles each of these by reverting the in-progress restore and pausing for operator review.
