# `guide` — Hermes plugin

Standalone repo: [`agentguides/hermes-plugin`](https://github.com/agentguides/hermes-plugin).
Ships the `guide_plugin` Python package (`src/guide_plugin/`), the walk Skill
triple, and the Hermes registration entrypoint.

Per-profile install of the [`guide-cli`](https://github.com/agentguides/runtime)
runtime under Hermes:

- registers `mcp_servers.guide` in the profile's `config.yaml` via a stable
  wrapper that execs `guide mcp` with the right environment overlay;
- surfaces the walk Skill triple (`walk`, `walk-observer`, `walk-inline`);
- builds a per-profile *view* — a symlink farm inside the plugin's own
  `.local/library-view/` exposing whichever subset of
  `$GUIDE_HOME/library/` the profile's policy admits;
- background-syncs the library through the Hermes cron template;
- tags every walk record with `harness: hermes` + `scope: <profile-name>`
  so the centralized state backend at `$GUIDE_HOME/state/` filters by profile.

## Install

```bash
hermes plugins install agentguides/hermes-plugin --enable
# or, from a local checkout:
git clone git@github.com:agentguides/hermes-plugin.git
hermes plugins install ./hermes-plugin --enable
```

On first run the plugin:

1. ensures `guide` is on PATH (auto-`uv tool install guide-cli` when `uv`
   is available; otherwise prints operator instructions);
2. derives the profile *scope name* from `$HERMES_HOME` (`default` for the
   root profile, otherwise the basename of `$HERMES_HOME`);
3. creates `$HERMES_HOME/plugins/guide/.local/{profile.toml,library-view/}`
   (policy = `all`, empty include list);
4. symlinks `$HERMES_HOME/cron/guide-sync.json` → the plugin's cron template;
5. pulls the configured default Books/Guides into `$GUIDE_HOME/library/`;
6. applies the symlink farm so the MCP server sees the library view.

## Uninstall

```bash
hermes guide uninstall-self
hermes plugins remove guide
```

`hermes guide uninstall-self` removes everything *this* profile install
created (`.local/`, the cron symlink) and prints what to do next. The
centralized library + state at `$GUIDE_HOME/` is preserved unless you
pass one of:

- `--purge-library` — remove `$GUIDE_HOME/library/` (refuses if another
  profile still has the plugin installed).
- `--purge-state` — remove `$GUIDE_HOME/state/` (destructive — every walk
  record across every harness + scope; warned).
- `--purge-home` — remove `$GUIDE_HOME/` entirely (sources + cache +
  library + state).

## CLI

| Command | What it does |
|---|---|
| `hermes guide list`           | list this profile's view |
| `hermes guide pull <id>`      | fetch a Book/Guide into the central library |
| `hermes guide install <id>`   | pull + install into this profile's view |
| `hermes guide sync`           | refresh every library entry; re-apply the view |
| `hermes guide profile policy <all|none|include>` | set per-profile policy |
| `hermes guide profile include <kind:id>` | add to the include list |
| `hermes guide status`         | one-shot health check |
| `hermes guide uninstall-self` | remove this profile install |

## On-disk layout

```
$HERMES_HOME/                                 ← active Hermes profile root
├── config.yaml                               ← `mcp_servers.guide` lives here
├── cron/guide-sync.json → ../plugins/guide/cron/guide-sync.json     (symlink)
└── plugins/guide/                            ← THIS plugin (git-managed)
    ├── plugin.yaml
    ├── __init__.py                           ← register(ctx)
    ├── bin/guide-mcp-wrapper.sh
    ├── cron/guide-sync.json
    ├── skills/{walk,walk-observer,walk-inline}/SKILL.md
    └── .local/                               ← OPERATOR STATE (git-ignored)
        ├── profile.toml                      ← policy + include list
        └── library-view/{books,guides}/<id>  → $GUIDE_HOME/library/.../<id>
```

The plugin code in this tree is git-managed; `.local/` survives plugin updates
because `hermes plugins update guide` runs `git pull`, which doesn't touch
untracked files.

## Development

This repo ships a real Python package (`guide_plugin`) plus a test suite that
includes a genuine plugin↔runtime integration test (`tests/test_multi_profile.py`),
which imports both `guide_plugin` and the `guide-cli` runtime. The runtime is
resolved from the sibling checkout at `../runtime` via `[tool.uv.sources]`.

```bash
just test     # uv run pytest (editable-installs guide_plugin + sibling guide-cli)
just render   # regenerate skills/{walk,walk-observer,walk-inline}/SKILL.md
```

### Regenerating the walk Skills

`skills/{walk,walk-observer,walk-inline}/SKILL.md` are **derived artifacts** of
`guide_cli.resources.render_router_skill` / `render_walk_skill`. Do not hand-edit
them — run `just render` (or `uv run python scripts/render_plugin_skills.py`) and
commit the result. Re-rendering against the pinned runtime reproduces the
committed files byte-for-byte.

## See also

- [`guide-cli` runtime](https://github.com/agentguides/runtime) — the central
  library, symlink-farm view primitive, and pull sources this plugin drives.
