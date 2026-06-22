"""Smoke-test the `register(ctx)` entry point against a stub context.

We don't run Hermes itself — instead a `StubContext` records every
`register_*` call. The test asserts that Hermes-visible registrations
happen and that the first-run bootstrap runs to completion against the
fixture HERMES_HOME.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
PLUGIN_INIT = REPO_ROOT / "plugins" / "hermes-plugin" / "__init__.py"


class StubContext:
    def __init__(self) -> None:
        self.skills: list[tuple[str, str]] = []
        self.cli_commands: list[str] = []
        self.commands: list[str] = []
        self.hooks: list[str] = []

    def register_skill(self, name: str, path: str) -> None:
        self.skills.append((name, path))

    def register_cli_command(self, name, help, setup_fn, handler_fn) -> None:  # noqa: A002
        self.cli_commands.append(name)

    def register_command(self, name, handler, description) -> None:
        self.commands.append(name)

    def register_hook(self, event, callback) -> None:
        self.hooks.append(event)


def _load_plugin_module():
    """Import `plugins/hermes-plugin/__init__.py` as a fresh module."""
    spec = importlib.util.spec_from_file_location("hermes_guide_plugin", PLUGIN_INIT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules.pop("hermes_guide_plugin", None)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def hermes_home(tmp_path, monkeypatch):
    home = tmp_path / "hh"
    home.mkdir()
    plugin_root = home / "plugins" / "guide"
    plugin_root.mkdir(parents=True)
    live = REPO_ROOT / "plugins" / "hermes-plugin"
    (plugin_root / "cron").symlink_to(live / "cron")
    (plugin_root / "bin").symlink_to(live / "bin")
    (plugin_root / "skills").symlink_to(live / "skills")
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("GUIDE_HOME", str(tmp_path / "guide"))
    return home


def test_register_wires_skills_cli_slash_and_hooks(hermes_home, tmp_path):
    plugin = _load_plugin_module()
    ctx = StubContext()
    plugin.register(ctx)

    # Walk skill triple shows up.
    skill_names = {n for n, _ in ctx.skills}
    assert "walk" in skill_names
    assert "walk-observer" in skill_names
    assert "walk-inline" in skill_names

    # CLI subcommands.
    for verb in ("list", "pull", "install", "sync", "status", "profile", "uninstall-self"):
        assert verb in ctx.cli_commands

    # Slash `/sync`.
    assert "sync" in ctx.commands

    # on_session_start hook.
    assert "on_session_start" in ctx.hooks


def test_register_runs_first_run_bootstrap(hermes_home, tmp_path):
    plugin = _load_plugin_module()
    plugin.register(StubContext())

    bubble = hermes_home / "plugins" / "guide" / ".local"
    assert (bubble / "profile.toml").is_file()
    assert (bubble / "library-view" / "books").is_dir()
    assert (bubble / "library-view" / "guides").is_dir()

    jobs_json = hermes_home / "cron" / "jobs.json"
    assert jobs_json.is_file()
    on_disk = json.loads(jobs_json.read_text(encoding="utf-8"))
    assert any(j["name"] == "guide-sync" for j in on_disk)


def test_register_writes_mcp_servers_guide_into_config(hermes_home, tmp_path):
    plugin = _load_plugin_module()
    plugin.register(StubContext())
    cfg = hermes_home / "config.yaml"
    assert cfg.is_file()
    import yaml
    on_disk = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    entry = on_disk["mcp_servers"]["guide"]
    assert entry["env"]["GUIDE_HARNESS"] == "hermes"
    assert entry["env"]["GUIDE_SCOPE"]  # non-empty


def test_register_is_idempotent(hermes_home, tmp_path):
    """Calling register twice (simulating two Hermes boots) should converge."""
    plugin = _load_plugin_module()
    for _ in range(2):
        plugin.register(StubContext())
    jobs = json.loads(
        (hermes_home / "cron" / "jobs.json").read_text(encoding="utf-8")
    )
    assert sum(1 for j in jobs if j["name"] == "guide-sync") == 1
