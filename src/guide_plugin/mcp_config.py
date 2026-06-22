"""Read/write the ``mcp_servers.guide`` block in `$HERMES_HOME/config.yaml`.

Hermes's plugin context (per its docs) does NOT expose a
``register_mcp_server()`` method — MCP servers are config-driven. The plugin
mutates `config.yaml` in place, preserving every other key the operator may
have set. Other mcp_servers entries are LEFT UNTOUCHED (the file is shared).

We use PyYAML — Hermes itself ships it as a transitive dep, so the plugin can
rely on `yaml` being importable in the Hermes Python env. If we ever ship to
a Hermes runtime without PyYAML, this is the import to special-case.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


MCP_ENTRY_NAME = "guide"


def _atomic_write(target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(target)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise RuntimeError(f"{path}: invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"{path}: top-level YAML must be a mapping")
    return data


def desired_entry(
    *,
    wrapper_script: Path,
    guide_home: Path,
    view_root: Path,
    state_path: Path,
    scope: str,
) -> dict[str, Any]:
    """What the `mcp_servers.guide` block should look like.

    The wrapper itself sets the env overlay so concurrent walks under
    different scopes don't collide on a single global env block — but we
    also stash the same vars in `env:` so Hermes-side debugging is one
    `yq '.mcp_servers.guide'` away.
    """
    return {
        "command": str(wrapper_script),
        "env": {
            "GUIDE_HOME": str(guide_home),
            "GUIDE_LIBRARY_PATH": str(view_root),
            "GUIDE_STATE_PATH": str(state_path),
            "GUIDE_HARNESS": "hermes",
            "GUIDE_SCOPE": scope,
        },
    }


def install(
    config_yaml: Path,
    *,
    wrapper_script: Path,
    guide_home: Path,
    view_root: Path,
    state_path: Path,
    scope: str,
) -> dict[str, Any]:
    """Write/refresh `mcp_servers.guide` in `config.yaml`. Returns the entry."""
    data = _load_yaml(config_yaml)
    servers = data.get("mcp_servers")
    if not isinstance(servers, dict):
        servers = {}
        data["mcp_servers"] = servers
    entry = desired_entry(
        wrapper_script=wrapper_script,
        guide_home=guide_home,
        view_root=view_root,
        state_path=state_path,
        scope=scope,
    )
    servers[MCP_ENTRY_NAME] = entry
    _atomic_write(config_yaml, yaml.safe_dump(data, sort_keys=False))
    return entry


def remove(config_yaml: Path) -> bool:
    """Remove our entry from `mcp_servers`. Returns True if it was there.

    Other entries under `mcp_servers` survive. An empty `mcp_servers` block
    is collapsed away so we don't leave a YAML stub behind.
    """
    data = _load_yaml(config_yaml)
    servers = data.get("mcp_servers")
    if not isinstance(servers, dict) or MCP_ENTRY_NAME not in servers:
        return False
    servers.pop(MCP_ENTRY_NAME, None)
    if not servers:
        data.pop("mcp_servers", None)
    _atomic_write(config_yaml, yaml.safe_dump(data, sort_keys=False))
    return True
