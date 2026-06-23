"""Plugin updates must not clobber `.local/` operator state.

The plugin README + Plan §"What's centralized vs. harness-scoped" promise that
`hermes plugins update guide` (which runs `git pull` inside the plugin tree)
leaves the operator's per-profile `.local/profile.toml` + `.local/library-view/`
intact. The `.gitignore` ships the line that makes this true; this test
asserts the contract holds against the live plugin tree.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from guide_plugin import bootstrap
from guide_plugin.paths import compute
from guide_plugin.profile_config import ProfileConfig


REPO_ROOT = Path(__file__).resolve().parents[1]


def _stage_plugin(plugin_root: Path) -> None:
    live = REPO_ROOT
    plugin_root.mkdir(parents=True, exist_ok=True)
    for sub in ("cron", "bin", "skills"):
        link = plugin_root / sub
        if not link.exists():
            link.symlink_to(live / sub)


@pytest.fixture
def installed_profile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    hermes_home = home / ".hermes"
    _stage_plugin(hermes_home / "plugins" / "guide")
    guide_home = tmp_path / "guide"
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.setenv("GUIDE_HOME", str(guide_home))
    paths = compute(hermes_home=hermes_home, guide_home=guide_home)
    bootstrap.run(paths, defaults=ProfileConfig())
    return paths


def test_local_bubble_is_git_ignored() -> None:
    """The plugin's own .gitignore must declare `.local/`. Without that line,
    `hermes plugins update` could blow away operator state via a hard reset."""
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".local/" in gitignore.splitlines(), (
        ".gitignore must list `.local/` so operator "
        "state survives `hermes plugins update`."
    )


def test_custom_profile_toml_survives_plugin_file_change(installed_profile) -> None:
    """Simulate `hermes plugins update guide` — Hermes pulls the plugin tree
    (which only touches git-tracked files). We mimic that by touching a
    plugin source file and re-running `register()`-style bootstrap. The
    operator's `profile.toml` (an untracked file inside `.local/`) must
    survive bit-for-bit."""
    paths = installed_profile

    # Author a custom policy + include list that the operator would not want
    # silently rewritten by a plugin update.
    custom = ProfileConfig(
        policy="include",
        include=["book:db-ops", "guide:hello-walk"],
        default_books=["db-ops"],
        default_guides=["hello-walk"],
    )
    custom.save(paths.profile_toml)
    snapshot_before = paths.profile_toml.read_text(encoding="utf-8")

    # Simulate the update: mtime-bump a tracked plugin file. (A real
    # `git pull` would do this for any file the upstream changed.) We
    # touch the wrapper script — a real-world update target.
    wrapper = paths.wrapper_script.resolve()
    wrapper.touch()

    # Re-run bootstrap (what register() does on every session boot).
    report = bootstrap.run(paths, defaults=ProfileConfig())
    # First-run flag is False — bubble already existed.
    assert report.profile_created is False

    snapshot_after = paths.profile_toml.read_text(encoding="utf-8")
    assert snapshot_after == snapshot_before, (
        "operator's profile.toml was rewritten by bootstrap re-run"
    )
    # And the content stayed semantically identical.
    reloaded = ProfileConfig.load(paths.profile_toml)
    assert reloaded.policy == "include"
    assert reloaded.include == ["book:db-ops", "guide:hello-walk"]


def test_library_view_symlinks_survive_plugin_update(installed_profile) -> None:
    """Symlinks under `.local/library-view/` are operator state — created
    when the plugin applies the view, untouched by plugin updates."""
    paths = installed_profile

    target = paths.master_lib / "books" / "imaginary"
    target.mkdir(parents=True)
    (target / "BOOK.md").write_text("# stub", encoding="utf-8")
    link = paths.view / "books" / "imaginary"
    link.symlink_to(target.resolve())

    # Simulate plugin update.
    paths.wrapper_script.resolve().touch()
    bootstrap.run(paths, defaults=ProfileConfig())

    # Operator-authored symlink still here.
    assert link.is_symlink()
    assert link.resolve() == target.resolve()


def test_re_register_does_not_collapse_distinct_profile_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A plugin update that ships to BOTH profiles (default + work) must not
    cross-contaminate their bubbles. Two profiles, two registers, one update,
    each `.local/` independent."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    default_hermes = home / ".hermes"
    work_hermes = default_hermes / "profiles" / "work"
    for hh in (default_hermes, work_hermes):
        _stage_plugin(hh / "plugins" / "guide")
    guide_home = tmp_path / "guide"

    default_paths = compute(hermes_home=default_hermes, guide_home=guide_home)
    work_paths = compute(hermes_home=work_hermes, guide_home=guide_home)

    bootstrap.run(default_paths, defaults=ProfileConfig())
    bootstrap.run(work_paths, defaults=ProfileConfig())

    # Author divergent policies.
    ProfileConfig(policy="all", include=[]).save(default_paths.profile_toml)
    ProfileConfig(policy="include", include=["book:db-ops"]).save(work_paths.profile_toml)

    # Simulate plugin tree update affecting both installs.
    default_paths.wrapper_script.resolve().touch()
    work_paths.wrapper_script.resolve().touch()

    bootstrap.run(default_paths, defaults=ProfileConfig())
    bootstrap.run(work_paths, defaults=ProfileConfig())

    assert ProfileConfig.load(default_paths.profile_toml).policy == "all"
    assert ProfileConfig.load(work_paths.profile_toml).policy == "include"
    assert ProfileConfig.load(work_paths.profile_toml).include == ["book:db-ops"]
