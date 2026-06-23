# Changelog

All notable changes to `agentguides-hermes-plugin` are recorded here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows [SemVer](https://semver.org/).

## [0.5.5] — 2026-06-23 (standalone repo carve + agentguides rename + release automation)

> Theme: *the Hermes plugin carves out of the runtime monorepo into its own repo,
> picks up the `guide-cli` → `agentguides` dist/import rename, and gains
> release/compat automation so a tagged tree is a validated artifact.*

### Standalone repo carve

- The `guide` Hermes plugin (hatchling package `src/guide_plugin`) moved out of
  `runtime/plugins/hermes-plugin/` into its own repo (`agentguides/hermes-plugin`).
  The package, its pytest suite (including the `test_multi_profile.py`
  plugin↔runtime integration test), and the walk-Skill renderer came with it.
- `[tool.uv.sources] agentguides = {path="../runtime", editable=true}` resolves
  the runtime from the sibling checkout for local dev; the new
  `agentguides>=0.5.8,<0.6.0` dev-group constraint documents the verified-against
  range a non-editable resolve would use.

### `agentguides` rename

- The runtime dist/import is now `agentguides` (CLI `guide`); the render script,
  `test_skill_render_parity.py`, and `test_multi_profile.py` import `agentguides.*`.

### Release / compat automation

- `CHANGELOG.md` + `scripts/check_version_changelog.py` keep `[project].version`,
  the `plugin.yaml` manifest version, and the changelog in lockstep.
- `just` recipes (`test-core`, `verify-runtime`, `build`, `release-dryrun`, `tag`,
  `precommit`) make "validated, tagged tree" the unit of release (git-clone
  distribution — no wheel).
- `tests/test_harness_install.py` installs this plugin's walk Skills + MCP server
  registration into a throwaway `AG_HERMES_HOME` via the runtime's own
  `agentguides.setup` installer and asserts `mcp_servers.guide` is registered and
  the walk Skills are present.
- `ruff` + `[tool.ruff]`/`[tool.ruff.lint]` config (line-length 100, py310,
  select E4/E7/E9/F) mirror the runtime; `.pre-commit-config.yaml` runs ruff,
  the version/changelog check, and a render-drift guard.
