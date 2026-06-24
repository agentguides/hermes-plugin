---
name: db-backup
description: |
  Take a verified backup of a relational database via pgBackRest. Activate when
  the user asks to back up a database, run an ad-hoc snapshot, or prepare a
  restore point before a migration. Part of the `db-ops` plugin.
license: Apache-2.0
allowed-tools: Bash Read
metadata:
  type: guide
  guide:
    entry: GUIDE.md
    spec_version: "0.1.0"
    state_backend: markdown
---

# Database Backup

This Skill is a **Guide**. A Guide-aware harness loads `GUIDE.md` to begin a run.
