"""Path computation — `register(ctx)` calls this once, then everyone uses
the result. All paths are absolute and resolved; absolute symlinks survive
moves of either root.

Plan §3 "Compute paths":

    GUIDE_HOME   = $GUIDE_HOME or ~/.guide
    MASTER_LIB   = $GUIDE_HOME/library
    STATE        = $GUIDE_HOME/state
    BUBBLE       = $HERMES_HOME/plugins/guide/.local
    VIEW         = $BUBBLE/library-view          (what the MCP server reads)
    POLICY       = $BUBBLE/profile.toml
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PLUGIN_NAME = "guide"


def _resolve(value: str | os.PathLike) -> Path:
    return Path(os.path.expanduser(os.fspath(value))).resolve()


@dataclass(frozen=True)
class PluginPaths:
    """Every absolute path the plugin ever touches."""

    hermes_home: Path
    plugin_root: Path
    """`$HERMES_HOME/plugins/guide/` — git-managed plugin tree."""
    bubble: Path
    """`$plugin_root/.local/` — operator state, git-ignored, survives plugin updates."""
    profile_toml: Path
    view: Path
    cron_dir: Path
    cron_jobs_json: Path
    """`$HERMES_HOME/cron/jobs.json` — Hermes's single cron job file. We
    upsert our `guide-sync` entry here (Hermes doesn't scan per-file
    templates; see `cron.py`)."""
    cron_template: Path
    """`$plugin_root/cron/guide-sync.json` — reference template the plugin
    renders into the `jobs.json` entry."""
    config_yaml: Path
    """`$HERMES_HOME/config.yaml` — where `mcp_servers.guide` lands."""
    wrapper_script: Path
    """`$plugin_root/bin/guide-mcp-wrapper.sh` — referenced from config.yaml."""

    guide_home: Path
    master_lib: Path
    state: Path


def hermes_home_from_env() -> Path:
    """Return `$HERMES_HOME`, defaulting to `~/.hermes` for the root profile."""
    return _resolve(os.environ.get("HERMES_HOME") or "~/.hermes")


def guide_home_from_env() -> Path:
    """Return `$GUIDE_HOME`, defaulting to `~/.guide`."""
    return _resolve(os.environ.get("GUIDE_HOME") or "~/.guide")


def compute(
    *,
    hermes_home: Path | None = None,
    guide_home: Path | None = None,
) -> PluginPaths:
    """Materialize every path the plugin needs.

    Both roots can be passed explicitly (tests) or fall back to env vars.
    """
    hh = (hermes_home or hermes_home_from_env()).resolve()
    gh = (guide_home or guide_home_from_env()).resolve()
    plugin_root = hh / "plugins" / PLUGIN_NAME
    bubble = plugin_root / ".local"
    return PluginPaths(
        hermes_home=hh,
        plugin_root=plugin_root,
        bubble=bubble,
        profile_toml=bubble / "profile.toml",
        view=bubble / "library-view",
        cron_dir=hh / "cron",
        cron_jobs_json=hh / "cron" / "jobs.json",
        cron_template=plugin_root / "cron" / "guide-sync.json",
        config_yaml=hh / "config.yaml",
        wrapper_script=plugin_root / "bin" / "guide-mcp-wrapper.sh",
        guide_home=gh,
        master_lib=gh / "library",
        state=gh / "state",
    )
