---
name: db-restore
description: |
  Restore a database from a pgBackRest backup. Demonstrates cross-Guide rescue:
  on failure of `020-apply-restore`, delegates to the sibling `guide:db-rollback`
  Guide. Activate when the user asks to restore, roll back to a backup, or
  recover from data loss. Part of the `db-ops` plugin.
license: Apache-2.0
allowed-tools: Bash Read AskUserQuestion
metadata:
  type: guide
  guide:
    entry: GUIDE.md
    spec_version: "0.1.0"
    state_backend: markdown
---

# Database Restore

This Skill is a **Guide**. A Guide-aware harness loads `GUIDE.md` to begin a run.
