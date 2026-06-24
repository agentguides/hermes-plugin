# Changelog

All notable changes to `agentguides-hermes-plugin` are recorded here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows [SemVer](https://semver.org/).

## [0.1.0] — 2026-06-23 (first standalone release: repo carve + agentguides rename + release automation)

> Theme: *first release of the `guide` Hermes plugin as a standalone repo. It
> carves out of the runtime monorepo, picks up the `guide-cli` → `agentguides`
> dist/import rename, and gains release/compat automation so a tagged tree is a
> validated artifact.*

Versioned independently of the runtime: `0.1.0` is the first ecosystem release
(the pre-split `0.5.x` monorepo numbers never shipped). Compatibility with the
runtime is declared by the `requires.version` range below and proven green by
`just verify-runtime`.

### Standalone repo carve

- The `guide` Hermes plugin (hatchling package `src/guide_plugin`) moved out of
  `runtime/plugins/hermes-plugin/` into its own repo (`agentguides/hermes-plugin`).
  The package, its pytest suite (including the `test_multi_profile.py`
  plugin↔runtime integration test), and the walk-Skill renderer came with it.
- `[tool.uv.sources] agentguides = {path="../runtime", editable=true}` resolves
  the runtime from the sibling checkout for local dev; the
  `agentguides>=0.5.10,<0.6.0` dev-group constraint is the `requires.version`
  range — the verified-against runtime a non-editable resolve would use, and
  what `tests/test_requires_version.py` asserts the runtime-under-test satisfies.

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
