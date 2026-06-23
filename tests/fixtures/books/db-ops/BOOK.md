---
agent-guides: book/v0.1
id: db-ops
title: Database Operations
version: 0.1.0
description: Book of related database operations Guides — snapshot/restore, point-in-time recovery, and fast rollback — that share a domain and reference each other via bare-name cross-Guide refs.
guides:
  - id: db-backup
    role: primary
  - id: db-restore
    role: primary
  - id: db-rollback
    role: recovery
authors:
  - Brian Cripe
---

# Database operations — book

A three-Guide book demonstrating multiple primary Guides in one book plus a shared recovery Guide that gets delegated to from peer Guides.

## Reading order

- **db-backup** — take a fresh backup. Standalone, no recovery dependency.
- **db-restore** — restore from a chosen backup. On failure, delegates to `db-rollback` via bare-name reference.
- **db-rollback** — sibling rescue Guide invoked by `db-restore` on apply-failure. Runnable standalone too.
