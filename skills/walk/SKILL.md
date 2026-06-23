---
name: walk
description: |
  Walk an guide-cli Guide. Activate when the user asks to walk, run,
  execute, perform, or resume a Guide; or when they reference a multi-step
  workflow by name and want it driven end-to-end.
  Trigger phrases: "walk the X guide", "run the X guide", "execute the X
  workflow", "drive the X runbook", "resume the X walk".
license: MIT
allowed-tools: Bash
guide:
  runtime:
    router: true
    default_mode: observer
---

# `walk` — guide-cli walk Skill router

This Skill routes to the mode-specific walk Skill based on the runtime
environment. The guide-cli walk runtime supports two audit-mode
surfaces — **observer** and **in_band** (a.k.a. **inline**) — installed
side-by-side as `walk-observer` and `walk-inline`. Which one to use is a
per-walk choice driven by the MCP server's current mode.

## Resolve the active mode

Run one short shell check to determine which surface the MCP server is
serving for this walk:

```
echo "GUIDE_AUDIT_MODE=${GUIDE_AUDIT_MODE:-<unset>}"
```

Then route:

1. **`observer`** — activate the `walk-observer` Skill and follow its
   protocol (the hint surface: `walk_begin` / `walk_step` / `walk_end`).
2. **`in_band`** — activate the `walk-inline` Skill and follow its
   protocol (the state-direct surface: `walk_start_run` /
   `walk_append_event` / `walk_update_step` / `walk_set_status`).
3. **`<unset>`** (or anything else) — STOP and report
   `audit mode not configured; cannot walk`. The harness should have
   set `GUIDE_AUDIT_MODE` via the per-walk env overlay; an unset
   value means the harness setup was bypassed.

This router itself does not call any MCP tools — its only job is to
hand off to the right concrete Skill. After activation, all walk
mechanics live in `walk-observer` / `walk-inline`.

## Why two Skills?

The two surfaces differ in **who produces audit events**:

- **observer**: the harness observes the agent's tool-call stream and
  reconstructs audit events. The agent only emits *hints*
  (`walk_begin`, `walk_step` enter/exit, `walk_end`).
- **in_band**: the agent IS the audit source. Every state change goes
  through an explicit MCP tool call (`walk_append_event`,
  `walk_update_step`, etc.).

Each surface has a different tool inventory and different lifecycle
rules. Mixing them produces incoherent audit trails — hence the
hard-routed dispatch above.
