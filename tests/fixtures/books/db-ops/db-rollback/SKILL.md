---
name: db-rollback
description: |
  Sibling rescue Guide invoked by `db-restore` when an in-progress restore
  fails. Unwinds partial state (stops postgres, restores from prior data dir
  copy, reattaches replicas) and pauses for operator decision. Part of the
  `db-ops` plugin; not typically activated directly.
license: Apache-2.0
allowed-tools: Bash Read
metadata:
  type: guide
  guide:
    entry: GUIDE.md
---

# Database Rollback (rescue)

This Skill is a **Guide**. It is the rescue path for `db-restore`'s `020-apply-restore` step. Activate directly only if you're testing the rescue procedure.
