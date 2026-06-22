# `guide` — Hermes plugin

> **Status:** prototype in the `agent-guides` monorepo (`plugins/hermes-plugin/`).
> Once verified against a real Hermes install, this tree extracts cleanly into
> its own repo at `agentguides/hermes-plugin`.

Per-profile install of the [`guide-cli`](https://github.com/briancripe/agent-guides)
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
# or, during prototyping, from this repo:
hermes plugins install ./plugins/hermes-plugin --enable
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

## See also

- [`.planning/plans/v0.5.5-hermes-plugin.md`](../../.planning/plans/v0.5.5-hermes-plugin.md) — design.
- [`docs/cli/library.md`](../../docs/cli/library.md) — central library shape.
- [`docs/cli/view.md`](../../docs/cli/view.md) — the symlink-farm primitive.
- [`docs/cli/sources.md`](../../docs/cli/sources.md) — pull sources.
