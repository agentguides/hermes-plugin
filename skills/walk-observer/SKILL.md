---
name: walk-observer
description: |
  Walk a Guide. Activate when the user asks to walk, run,
  execute, perform, or resume a Guide; or when they reference a multi-step
  workflow by name and want it driven end-to-end.
  Trigger phrases: "walk the X guide", "run the X guide", "execute the X
  workflow", "drive the X runbook", "resume the X walk".
license: MIT
allowed-tools: Bash AskUserQuestion Read
guide:
  runtime:
    mode: observer
    capability: full
    features: ["linear-steps", "prereqs", "retry", "recover", "sub-walks", "branching", "agent-judgment-reasoning"]
---

# Walking a Guide

You are the Guide v0.2 runtime for this session. All state mutations go through the `guide` MCP server tools, never through direct file I/O on run files.

This Skill is configured for **observer mode**. A harness-side observer reconstructs tool calls, prompts, and step-reasoning prose into the audit log automatically. Your job is the small *hint surface* — call `walk_*` tools at step boundaries; let the observer do the rest.

If at session start you see `walk_start_run`, `walk_update_step`, `walk_append_event` in the MCP tools instead of the `walk_begin` / `walk_step` / `walk_end` hint set, the runtime degraded from observer to in_band because the observer was unhealthy at startup (ADR 012). Tell the user once, then ask them to re-run `guide setup` with `--mode inline` so the installed Skill matches the active toolset.


## Required MCP tools

- `walk_begin({guide_root, parent_run_id?}) → {run_id, position}` — start a walk. `parent_run_id` is set when this walk was triggered by a `guide_ref` action in a parent step.
- `walk_step({run_id, step_id, phase, verdict?, verify_result?, reasoning_anchor?}) → {position}` — step lifecycle hint. `phase: "enter"` opens a step; `phase: "exit"` closes it with a `verdict` (`succeeded` / `failed` / `skipped` / `rolled_back`).
- `walk_end({run_id, status}) → {position}` — terminate the walk with the run's final `RunStatus` (`succeeded` / `failed` / `abandoned`).
- `walk_mark_prereqs_checked({run_id, value: true}) → {run_id, position}` — project the prereqs-passed boolean into the run frontmatter.
- `walk_current({guide_id, wait_for_position?}) → {run_id, stale}` — check for an active run (used on resume).
- `walk_load_run({run_id, wait_for_position?}) → {run, stale}` — re-read state when you need it (resume, passing context to a verifier).
- `walk_read_step({guide_root, step_id})` — read a step's frontmatter and body.


## Prerequisites phase

Run prerequisites declared in `GUIDE.md` before any step. For each:

- `performer: agent` and a `check:` script provided → run via `Bash`.
- `performer: human` → ask via `AskUserQuestion`.

When all prereqs pass:

- `walk_mark_prereqs_checked({run_id, value: true})`


Prereqs are NOT steps; do not synthesize a `prereqs` step in the audit.

## Step protocol

For each step in topological order:

1. `walk_step({phase: "enter", step_id})`. Save the returned `position` if you need read-after-write later.
2. Execute the action by `action.type`:
   - **script** → `Bash`. Run the ABSOLUTE path from `walk_read_step`'s `resolved_scripts.action` (cwd-independent; the bare `action.script` is Guide-root-relative and will fail if your shell's cwd isn't the Guide root). Honor `args` + `timeout_seconds`.
   - **manual** / **prompt** → emit instructions; yield; the next user message is the report (the observer captures it as `human.report` automatically).
   - **skill_ref** → activate the referenced Skill.
   - **guide_ref** → call `walk_begin({guide_root: <sub>, parent_run_id: <current>})`; block until the sub-walk terminates.
3. Apply `interactions` per `when` using `AskUserQuestion` (`confirm` / `choice` / `text`) or tool-less turn capture (`multiline`).
4. Execute the verifier by `verify.type`:
   - **script** → `Bash` (run `resolved_scripts.verify`, the absolute path); check exit against `success_exit` (default 0). If `output_schema: json`, parse stdout into a dict and pass as `verify_result`.
   - **agent_judgment** → reason briefly in prose (the observer captures it verbatim as `step.reasoning`), then `walk_step({phase: "exit", verdict, reasoning_anchor: true})`.
   - **human_confirm** → `AskUserQuestion` with yes/no.
   - **none** → action completion is success.
5. `walk_step({phase: "exit", verdict, verify_result?})`. Pass `verify_result` when the verifier produced structured output (script exit + parsed JSON).


## Failure handling

When a verifier rejects or an action exits non-zero, honor the step's `on_failure.strategy`:

- **abort** → terminate the run (mode-specific tool call below).
- **retry** → re-execute the action up to the declared retry count.
- **recover** → start a rescue sub-walk for the declared `recover_with` Guide with `parent_run_id` set (observer) or as a child run (inline). On success, if `resume_after_recovery: true`, retry the failed step.
- **ask** → `AskUserQuestion` with options "retry / abort / mark succeeded / abandon".


## Termination

When all steps reach terminal status without failure:

- `walk_end({run_id, status: "succeeded"})`


## Strict rules

- Never touch run files directly — only through MCP tools.
- Use **only** the `walk_*` hint-surface tools (plus `Bash`, `AskUserQuestion`, `Read`). The fine-grained inline-mode mutators (`walk_start_run`, `walk_update_step`, `walk_append_event`, …) don't exist in this mode (ADR 010).
- Thread `position` into reads via `wait_for_position` if you need read-after-write consistency. If a read returns `stale: true`, the observer hasn't caught up within ~2s; either retry or accept the stale view and move on.
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
