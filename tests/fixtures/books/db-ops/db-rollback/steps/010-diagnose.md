---
step:
  id: diagnose
  title: Diagnose the cause of the restore failure
  performer: agent
  action:
    type: script
    script: scripts/diagnose.sh
  verify:
    type: script
    script: scripts/diagnose.sh
    args: ["--verify"]
    success_exit: 0
    output_schema: json
  on_failure:
    strategy: abort
  estimated_duration_minutes: 3
  tags: [diagnostic]
---

# What this step does

Captures `pgbackrest info`, `df -h`, postgres log tail, and the in-progress restore status into a structured JSON blob the next step can read.

# Success criteria

- `verify.output.cause` is one of `{disk_space, permission_denied, replica_misconfigured, other}`.
