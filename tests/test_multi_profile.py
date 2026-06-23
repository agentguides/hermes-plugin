"""Two Hermes profiles sharing one $GUIDE_HOME library — the plan's central
multi-profile design claim (Plan verification steps #4-#7).

What's exercised here:

- Two distinct PluginPaths (one default profile, one named) point at the SAME
  master library + state path, but distinct bubbles + views.
- Each profile's `mcp_config.install` writes its own `GUIDE_SCOPE` into its
  own `config.yaml` — neither leaks into the other.
- A library entry installed once is symlinked into BOTH views; per-profile
  policy changes only affect the profile they're set on.
- Walk records spawned with each profile's env tag with that profile's scope;
  centralized `list_all_runs(filter={harness, scope})` filters correctly.

Plugin scope derivation is exercised directly via `derive_scope()` — Hermes
isn't in the loop here; the bootstrap + mcp-config writer + view apply are
the things we own and the things that could drift.

NOTE (v0.5.7/M3): this is the one plugin test that is a *plugin↔runtime
integration* test — it imports `guide_plugin` (this plugin) AND, inside the
bodies below, `guide_cli` (the runtime: pack/library/view/state). It is the
sole exception to "plugin tests need zero runtime source." When this plugin
becomes a standalone repo (see `public-split.md`), it must declare `agentguides`
as a dev/test dependency so this test can import it. All other tests in this
suite are runtime-source-free.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from guide_plugin import bootstrap, mcp_config
from guide_plugin.paths import compute
from guide_plugin.profile_config import ProfileConfig
from guide_plugin.scope import derive_scope


# This is the sole plugin↔runtime integration test: its bodies import the runtime
# (`agentguides.library`/`pack`/`view`/`state`). Mark the whole module
# `requires_runtime` so the runtime-source-free core run (`pytest -m "not
# requires_runtime"`) excludes it and `just verify-runtime` includes it against
# the BUILT runtime wheel.
pytestmark = pytest.mark.requires_runtime

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_BOOK = REPO_ROOT / "tests" / "fixtures" / "books" / "db-ops"


def _stage_plugin(plugin_root: Path) -> None:
    """Symlink the static-content subtrees the bootstrap consults so this
    test exercises the live plugin tree without copying it twice."""
    live = REPO_ROOT
    plugin_root.mkdir(parents=True, exist_ok=True)
    for sub in ("cron", "bin", "skills"):
        link = plugin_root / sub
        if not link.exists():
            link.symlink_to(live / sub)


@pytest.fixture
def two_profile_world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Stand up `$HOME/.hermes/` (default profile root) + a sibling at
    `$HOME/.hermes/profiles/work/`, sharing one `$GUIDE_HOME`.

    `derive_scope()` keys off the *real* `~/.hermes` to identify which profile
    a path represents; we monkeypatch `Path.home()` so the test stays sealed.
    """
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setenv("HOME", str(home))

    default_hermes = home / ".hermes"
    named_hermes = default_hermes / "profiles" / "work"
    for hh in (default_hermes, named_hermes):
        _stage_plugin(hh / "plugins" / "guide")
    guide_home = tmp_path / "guide"
    monkeypatch.setenv("GUIDE_HOME", str(guide_home))

    default_paths = compute(hermes_home=default_hermes, guide_home=guide_home)
    work_paths = compute(hermes_home=named_hermes, guide_home=guide_home)
    return default_paths, work_paths


# ---------------------------------------------------------------- shape


def test_paths_share_library_and_state_but_distinct_bubbles(two_profile_world) -> None:
    default_paths, work_paths = two_profile_world
    # Shared.
    assert default_paths.master_lib == work_paths.master_lib
    assert default_paths.state == work_paths.state
    # Distinct.
    assert default_paths.bubble != work_paths.bubble
    assert default_paths.view != work_paths.view
    assert default_paths.config_yaml != work_paths.config_yaml


def test_scope_derives_default_and_named_correctly(two_profile_world) -> None:
    default_paths, work_paths = two_profile_world
    assert derive_scope(default_paths.hermes_home) == "default"
    assert derive_scope(work_paths.hermes_home) == "work"


# ---------------------------------------------------------------- bootstrap


def test_each_profile_bootstraps_its_own_bubble(two_profile_world) -> None:
    default_paths, work_paths = two_profile_world
    bootstrap.run(default_paths, defaults=ProfileConfig())
    bootstrap.run(work_paths, defaults=ProfileConfig())

    assert default_paths.profile_toml.is_file()
    assert work_paths.profile_toml.is_file()
    # Independent file objects (different paths even if same content).
    assert default_paths.profile_toml != work_paths.profile_toml
    # Each profile has its own cron jobs file.
    assert default_paths.cron_jobs_json.is_file()
    assert work_paths.cron_jobs_json.is_file()
    assert default_paths.cron_jobs_json != work_paths.cron_jobs_json


def test_mcp_config_writes_distinct_scopes_per_profile(two_profile_world) -> None:
    default_paths, work_paths = two_profile_world
    mcp_config.install(
        default_paths.config_yaml,
        wrapper_script=default_paths.wrapper_script,
        guide_home=default_paths.guide_home,
        view_root=default_paths.view,
        state_path=default_paths.state,
        scope=derive_scope(default_paths.hermes_home),
    )
    mcp_config.install(
        work_paths.config_yaml,
        wrapper_script=work_paths.wrapper_script,
        guide_home=work_paths.guide_home,
        view_root=work_paths.view,
        state_path=work_paths.state,
        scope=derive_scope(work_paths.hermes_home),
    )
    default_cfg = yaml.safe_load(
        default_paths.config_yaml.read_text(encoding="utf-8")
    )
    work_cfg = yaml.safe_load(work_paths.config_yaml.read_text(encoding="utf-8"))
    assert default_cfg["mcp_servers"]["guide"]["env"]["GUIDE_SCOPE"] == "default"
    assert work_cfg["mcp_servers"]["guide"]["env"]["GUIDE_SCOPE"] == "work"
    # And the views differ so per-profile policy stays sealed.
    assert (
        default_cfg["mcp_servers"]["guide"]["env"]["GUIDE_LIBRARY_PATH"]
        != work_cfg["mcp_servers"]["guide"]["env"]["GUIDE_LIBRARY_PATH"]
    )


# ---------------------------------------------------------------- shared library + per-view policy


def test_library_entry_is_shared_views_independent(two_profile_world) -> None:
    """Install one Book into the shared library; each profile applies its own
    view; verify both views point at the SAME inode."""
    from agentguides.library import install_to_library
    from agentguides.pack import pack_book
    from agentguides.view import ViewConfig, apply_symlink_farm

    default_paths, work_paths = two_profile_world
    bootstrap.run(default_paths, defaults=ProfileConfig())
    bootstrap.run(work_paths, defaults=ProfileConfig())

    # Pack + install one book into the shared master library.
    dist = default_paths.guide_home / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    pack = pack_book(EXAMPLE_BOOK, out_dir=dist)
    install_to_library(pack.bundle_path, root=default_paths.master_lib)

    # Each profile applies its own view; both pull from the same library.
    apply_symlink_farm(default_paths.master_lib, default_paths.view, ViewConfig())
    apply_symlink_farm(work_paths.master_lib, work_paths.view, ViewConfig())

    default_link = default_paths.view / "books" / "db-ops"
    work_link = work_paths.view / "books" / "db-ops"
    assert default_link.is_symlink() and work_link.is_symlink()
    # Both resolve to the same library inode (the design's whole point).
    assert default_link.resolve() == work_link.resolve()
    assert default_link.resolve() == (default_paths.master_lib / "books" / "db-ops").resolve()


def test_per_profile_policy_does_not_leak(two_profile_world) -> None:
    """`work` switches to policy=none; `default` keeps policy=all. Library
    content is unchanged; only `work`'s view goes empty."""
    from agentguides.library import install_to_library
    from agentguides.pack import pack_book
    from agentguides.view import ViewConfig, apply_symlink_farm

    default_paths, work_paths = two_profile_world
    bootstrap.run(default_paths, defaults=ProfileConfig())
    bootstrap.run(work_paths, defaults=ProfileConfig())

    dist = default_paths.guide_home / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    pack = pack_book(EXAMPLE_BOOK, out_dir=dist)
    install_to_library(pack.bundle_path, root=default_paths.master_lib)

    apply_symlink_farm(default_paths.master_lib, default_paths.view, ViewConfig())
    # Work flips to policy=none.
    work_config = ProfileConfig.load(work_paths.profile_toml)
    work_config.policy = "none"
    work_config.save(work_paths.profile_toml)
    apply_symlink_farm(work_paths.master_lib, work_paths.view, ViewConfig(policy="none"))

    assert (default_paths.view / "books" / "db-ops").is_symlink()
    assert not (work_paths.view / "books" / "db-ops").exists()
    # Master library content untouched.
    assert (default_paths.master_lib / "books" / "db-ops" / "BOOK.md").is_file()


# ---------------------------------------------------------------- multi-tenant walk state


def test_walks_from_two_profiles_filter_by_scope(
    two_profile_world, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Walks spawned with each profile's `GUIDE_HARNESS`/`GUIDE_SCOPE` env land
    in the SAME state backend but filter cleanly by scope. Plan verification
    step #7 — the multi-tenant tagging that justifies the v0.5.5 design."""
    from agentguides.state import MarkdownBackend

    default_paths, work_paths = two_profile_world
    backend = MarkdownBackend(default_paths.state)

    monkeypatch.setenv("GUIDE_HARNESS", "hermes")
    monkeypatch.setenv("GUIDE_SCOPE", derive_scope(default_paths.hermes_home))
    default_run = backend.start_run("hello-walk", "0.1.0")

    monkeypatch.setenv("GUIDE_SCOPE", derive_scope(work_paths.hermes_home))
    work_run = backend.start_run("hello-walk", "0.1.0")
    monkeypatch.delenv("GUIDE_SCOPE")

    # Both runs landed in the same shared state dir.
    assert backend.state_path == default_paths.state == work_paths.state

    # Filtering by scope:
    default_only = backend.list_all_runs({"harness": "hermes", "scope": "default"})
    assert {r.run_id for r in default_only} == {default_run}

    work_only = backend.list_all_runs({"harness": "hermes", "scope": "work"})
    assert {r.run_id for r in work_only} == {work_run}
