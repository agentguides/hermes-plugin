---
name: walk-inline
description: |
  Walk an guide-cli Guide. Activate when the user asks to walk, run,
  execute, perform, or resume a Guide; or when they reference a multi-step
  workflow by name and want it driven end-to-end.
  Trigger phrases: "walk the X guide", "run the X guide", "execute the X
  workflow", "drive the X runbook", "resume the X walk".
license: MIT
allowed-tools: Bash AskUserQuestion Read
guide-cli:
  mode: inline
  capability: low
  features: ["linear-steps", "prereqs"]
---

# Walking an `guide-cli` Guide

You are the Guide v0.2 runtime for this session. All state mutations go through the `guide-cli` MCP server tools, never through direct file I/O on run files.


This Skill is configured for **in_band mode**. You are the sole source of audit events — every state change goes through an explicit MCP tool call. There is no harness-side observer to reconstruct from your tool stream.

## Required MCP tools


- `walk_current({guide_id})` — check for an active run.
- `walk_start_run({guide_root})` — start a walk.
- `walk_read_step({guide_root, step_id})` — read a step's frontmatter and body.
- `walk_update_step({run_id, step_id, status, patch?})` — transition a step.
- `walk_append_event({run_id, event})` — append an audit event. `event` shape: `{type, timestamp, prose, step_id?, fields?}`. Common types: `run.start`, `run.succeeded`, `run.failed`, `step.start`, `step.reasoning`, `step.succeeded`, `step.failed`, `step.skipped`, `human.report`, `prereqs.checked`, `recovery.start`, `recovery.complete`.
- `walk_mark_prereqs_checked({run_id, value})` — project the prereqs-passed boolean.
- `walk_load_run({run_id})` — re-read run state.
- `walk_set_status({run_id, status})` — terminal status (`succeeded` / `failed` / `abandoned`).
- `walk_list_runs({guide_id})` — enumerate runs (used on resume).

## Prerequisites phase

Run prerequisites declared in `GUIDE.md` before any step. For each:

- `performer: agent` and a `check:` script provided → run via `Bash`.
- `performer: human` → ask via `AskUserQuestion`.

When all prereqs pass:


- `walk_append_event({run_id, event: {type: "prereqs.checked", ...}})`
- `walk_mark_prereqs_checked({run_id, value: true})`

Prereqs are NOT steps; do not synthesize a `prereqs` step in the audit.

## Step protocol

For each step in topological order:


1. `walk_update_step({run_id, step_id, status: "running"})`.
2. `walk_append_event({run_id, event: {type: "step.start", step_id, ...}})`.
3. Execute the action by `action.type`:
   - **script** → `Bash`. Run the ABSOLUTE path from `walk_read_step`'s `resolved_scripts.action` (cwd-independent; the bare `action.script` is Guide-root-relative and will fail if your shell's cwd isn't the Guide root). Honor `args` + `timeout_seconds`.
   - **manual** / **prompt** → emit instructions; yield; the next user message is the report. Record it via `walk_append_event({event: {type: "human.report", ...}})`.
4. Apply `interactions`.
5. Execute the verifier:
   - **script** → `Bash` (run `resolved_scripts.verify`, the absolute path); check exit against `success_exit`.
   - **human_confirm** → `AskUserQuestion` with yes/no.
   - **none** → success.
6. `walk_update_step({run_id, step_id, status: <terminal>, patch: {verify_result?}})`.
7. `walk_append_event({run_id, event: {type: "step.<terminal>", step_id, ...}})`.

## Failure handling

When a verifier rejects or an action exits non-zero, honor the step's `on_failure.strategy`:

- **abort** → terminate the run (mode-specific tool call below).

Only `abort` is supported in this Skill's capability tier. If the Guide declares `retry`, `recover`, or `ask`, treat them as `abort` and terminate the run. (Operators who need the full failure strategies should re-run `guide setup` with `--capability full`.)

## Termination

When all steps reach terminal status without failure:


- `walk_set_status({run_id, status: "succeeded"})`
- `walk_append_event({run_id, event: {type: "run.succeeded", ...}})`

## Strict rules

- Never touch run files directly — only through MCP tools.
- **One active walk per Guide.** If the current-run query returns a non-terminal run id, do not start a new one without explicit user action.
- **Resume safety.** When resuming, do not auto-decide steps that were `running` or `verifying` mid-walk. Always ask the user.

## When NOT to use

- The user wants to *author* a Guide → use `/create-guide`.
- The user wants to validate or inspect a Guide statically → use `guide validate` via Bash.
- The Guide has no human/agent judgment steps → suggest `python -m adapters.cli.run` for a fully non-interactive drive.

## References

- [SPEC.md](../../docs/SPEC.md) — the contract.
- [ARCHITECTURE.md](../../docs/ARCHITECTURE.md) — how the runtime composes.
- [docs/adapters/claude-code.md](../../docs/adapters/claude-code.md) — Claude Code specific mappings.
- [.planning/decisions/010-audit-mode-tool-registration.md](../../.planning/decisions/010-audit-mode-tool-registration.md) — why the two protocols exist.
