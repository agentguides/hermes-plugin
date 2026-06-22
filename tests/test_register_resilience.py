"""`register(ctx)` must stay alive when `guide` isn't on PATH.

Plan §"Phase C — register(ctx)" promises a defensive shape: any single step
failing logs and continues so the operator can recover the bubble manually
if `guide-cli` isn't installable in their environment.

This file proves the contract: when guide-cli AND uv are both missing, the
plugin still registers Skills + CLI + hook + slash, writes mcp_servers.guide
into config.yaml, upserts the cron entry, and creates `.local/` — only the
initial library pull + view apply fail (and they fail gracefully via
BootstrapReport.pull_failures).

An operator who installs the plugin before installing guide-cli can
`pipx install guide-cli` afterwards and `hermes guide sync` to recover
without reinstalling the plugin.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
PLUGIN_INIT = REPO_ROOT / "plugins" / "hermes-plugin" / "__init__.py"


class StubContext:
    def __init__(self) -> None:
        self.skills: list[tuple[str, str]] = []
        self.cli_commands: list[str] = []
        self.commands: list[str] = []
        self.hooks: list[str] = []

    def register_skill(self, name, path, description: str = "") -> None:
        assert isinstance(path, Path)
        assert path.exists()
        self.skills.append((name, str(path)))

    def register_cli_command(self, name, help, setup_fn, handler_fn) -> None:  # noqa: A002
        self.cli_commands.append(name)

    def register_command(self, name, handler, description) -> None:
        self.commands.append(name)

    def register_hook(self, event, callback) -> None:
        self.hooks.append(event)


def _load_plugin_module():
    spec = importlib.util.spec_from_file_location("hermes_guide_plugin", PLUGIN_INIT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules.pop("hermes_guide_plugin", None)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def fixture_hermes_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
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


@pytest.fixture
def hide_guide_and_uv(monkeypatch: pytest.MonkeyPatch):
    """Make both `guide` and `uv` look missing on PATH. The plugin's
    `ensure_guide_installed` should raise GuideNotInstalled — `_do_register`
    catches that and continues with the remaining steps."""
    import guide_plugin.cli as plugin_cli

    monkeypatch.setattr(plugin_cli, "guide_on_path", lambda: False)
    monkeypatch.setattr(plugin_cli, "uv_on_path", lambda: False)


def test_register_completes_when_guide_missing(
    fixture_hermes_home: Path, hide_guide_and_uv, capsys
) -> None:
    plugin = _load_plugin_module()
    ctx = StubContext()
    plugin.register(ctx)

    # Filesystem invariants survived the GuideNotInstalled exception.
    bubble = fixture_hermes_home / "plugins" / "guide" / ".local"
    assert (bubble / "profile.toml").is_file()
    assert (bubble / "library-view" / "books").is_dir()
    assert (bubble / "library-view" / "guides").is_dir()

    cfg = yaml.safe_load(
        (fixture_hermes_home / "config.yaml").read_text(encoding="utf-8")
    )
    assert cfg["mcp_servers"]["guide"]["env"]["GUIDE_HARNESS"] == "hermes"

    jobs_json = fixture_hermes_home / "cron" / "jobs.json"
    assert jobs_json.is_file()

    # Skills + CLI subcommands + hook + slash STILL registered (these don't
    # need the guide binary at register time).
    assert {"walk", "walk-observer", "walk-inline"}.issubset(
        {name for name, _ in ctx.skills}
    )
    for verb in (
        "list", "pull", "install", "sync", "status", "profile", "uninstall-self"
    ):
        assert verb in ctx.cli_commands
    assert "sync" in ctx.commands
    assert "on_session_start" in ctx.hooks

    # The plugin logged the missing-binary diagnostic.
    captured = capsys.readouterr()
    assert "guide-cli is not installed" in captured.err


def test_register_skill_failure_does_not_abort(
    fixture_hermes_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If `ctx.register_skill` raises for any Skill, the rest of the plugin's
    register() must still run — Hermes shouldn't be unable to boot because
    of one bad Skill registration."""
    plugin = _load_plugin_module()

    class BrokenCtx(StubContext):
        def register_skill(self, name, path, description: str = "") -> None:
            raise RuntimeError(f"broken skill: {name}")

    ctx = BrokenCtx()
    plugin.register(ctx)

    # MCP config, cron, bubble all still happened.
    assert (fixture_hermes_home / "config.yaml").is_file()
    assert (fixture_hermes_home / "cron" / "jobs.json").is_file()
    assert (
        fixture_hermes_home / "plugins" / "guide" / ".local" / "profile.toml"
    ).is_file()
    # Skills list is empty because every register_skill raised.
    assert ctx.skills == []
    # CLI + hooks + slash still wired.
    assert "uninstall-self" in ctx.cli_commands
    assert "on_session_start" in ctx.hooks


def test_register_top_level_exception_does_not_crash_hermes(
    fixture_hermes_home: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """If something deeper than a try/except trips (a bug in our code),
    `register()` must NEVER propagate — Hermes uses it as a "should I keep
    going?" gate, and the user-visible failure mode is "no guide tools" not
    "Hermes won't boot"."""
    plugin = _load_plugin_module()

    # Force a top-level explosion by making compute() raise.
    import guide_plugin.paths as plugin_paths

    def boom(**kwargs):
        raise RuntimeError("synthetic configuration error")

    monkeypatch.setattr(plugin_paths, "compute", boom)

    ctx = StubContext()
    # register() must NOT raise — the test will fail if it does.
    plugin.register(ctx)
    captured = capsys.readouterr()
    assert "synthetic configuration error" in (captured.err + captured.out)
