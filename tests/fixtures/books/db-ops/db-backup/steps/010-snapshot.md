---
step:
  id: snapshot
  title: Trigger pgBackRest full backup
  performer: agent
  action:
    type: script
    script: scripts/snapshot.sh
    timeout_seconds: 1800
  verify:
    type: script
    script: scripts/snapshot.sh
    args: ["--verify"]
    success_exit: 0
    output_schema: json
  on_failure:
    strategy: abort
  estimated_duration_minutes: 10
  tags: [snapshot]
---

# What this step does

Calls `pgbackrest --stanza=main backup --type=full`. The verify pass re-reads the stanza to confirm a fresh backup label exists.

# Success criteria

- Action script exits 0.
- Verify script exits 0 and emits a JSON `{snapshot_id, timestamp}` payload.
