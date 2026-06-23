---
step:
  id: pick-backup
  title: Pick the backup label to restore to
  performer: agent
  action:
    type: script
    script: scripts/list-backups.sh
  verify:
    type: script
    script: scripts/list-backups.sh
    args: ["--verify"]
    success_exit: 0
    output_schema: json
  on_failure:
    strategy: abort
  estimated_duration_minutes: 5
  tags: [discovery]
---

# What this step does

Lists candidate backup labels from the pgBackRest stanza and picks the most recent full backup unless the operator overrides via interaction.

# Success criteria

- A non-empty `backup_id` is selected and recorded in `verify.output`.
