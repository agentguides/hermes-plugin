"""Handler bodies for the plugin's CLI subcommands + the `/sync` slash command.

Every handler is a thin shell over the `guide` binary, applying the
plugin's standard `GUIDE_*` env overlay so each shellout is tagged
consistently with the active scope.
"""

from __future__ import annotations

from . import cli as _cli
from . import uninstall as _uninstall
from .paths import PluginPaths
from .profile_config import ProfileConfig
from .scope import derive_scope


def _overlay(paths: PluginPaths) -> dict[str, str]:
    return _cli.guide_env_overlay(
        guide_home=paths.guide_home,
        view_root=paths.view,
        state_path=paths.state,
        scope=derive_scope(paths.hermes_home),
    )


# ---- CLI: `hermes guide <verb>` -----------------------------------------


def list_view(paths: PluginPaths, args: list[str] | None = None) -> int:
    res = _cli.run_guide(
        ["view", "list", str(paths.view)],
        env_overlay=_overlay(paths),
        check=False,
    )
    return res.returncode


def pull(paths: PluginPaths, id_arg: str) -> int:
    res = _cli.run_guide(
        ["pull", id_arg],
        env_overlay=_overlay(paths),
        check=False,
    )
    return res.returncode


def install(paths: PluginPaths, id_arg: str) -> int:
    """Equivalent to `guide sync <id> --view <view>` — pull + view re-apply."""
    res = _cli.run_guide(
        ["sync", id_arg, "--view", str(paths.view)],
        env_overlay=_overlay(paths),
        check=False,
    )
    return res.returncode


def sync(paths: PluginPaths, args: list[str] | None = None) -> int:
    """Refresh every entry currently in the library and re-apply the view."""
    res = _cli.run_guide(
        ["sync", "--view", str(paths.view)],
        env_overlay=_overlay(paths),
        check=False,
    )
    return res.returncode


def status(paths: PluginPaths, args: list[str] | None = None) -> int:
    """Print a one-shot health summary."""
    print(f"plugin root:    {paths.plugin_root}")
    print(f"bubble (.local): {paths.bubble}")
    print(f"profile.toml:   {paths.profile_toml}")
    print(f"view root:      {paths.view}")
    print(f"library:        {paths.master_lib}")
    print(f"state:          {paths.state}")
    print(f"scope:          {derive_scope(paths.hermes_home)}")
    print(f"guide on PATH:  {_cli.guide_on_path()}")
    print()
    print("--- view list ---")
    return list_view(paths)


def profile_policy(paths: PluginPaths, policy_arg: str) -> int:
    """`hermes guide profile policy <all|none|include>`."""
    if policy_arg not in ("all", "none", "include"):
        print(f"error: policy must be 'all', 'none', or 'include' — got {policy_arg!r}")
        return 2
    cfg = ProfileConfig.load(paths.profile_toml)
    cfg.policy = policy_arg  # type: ignore[assignment]
    cfg.save(paths.profile_toml)
    print(f"policy → {policy_arg}; re-applying view…")
    return install(paths, ".")  # reapplies the view without pulling new content


def profile_include(paths: PluginPaths, entry: str) -> int:
    """`hermes guide profile include <kind:id>` — add to allowlist."""
    if ":" not in entry or entry.split(":")[0] not in ("book", "guide"):
        print("error: include entry must be 'book:<id>' or 'guide:<id>'")
        return 2
    cfg = ProfileConfig.load(paths.profile_toml)
    if entry not in cfg.include:
        cfg.include.append(entry)
        cfg.save(paths.profile_toml)
    print(f"include += {entry}; re-applying view…")
    return install(paths, ".")


def uninstall_self(
    paths: PluginPaths,
    *,
    purge_library: bool = False,
    purge_state: bool = False,
    purge_home: bool = False,
) -> int:
    report = _uninstall.run(
        paths,
        purge_library=purge_library,
        purge_state=purge_state,
        purge_home=purge_home,
    )
    print(f"view symlinks cleared: {report.view_symlinks_cleared}")
    print(f"cron job removed:      {report.cron_job_removed}")
    print(f"mcp entry removed:     {report.mcp_entry_removed}")
    print(f"bubble removed:        {report.bubble_removed}")
    if report.library_purged:
        print("library purged.")
    if report.state_purged:
        print("state purged (across all harnesses + scopes).")
    if report.home_purged:
        print("$GUIDE_HOME purged.")
    for refusal in report.refusals:
        print(f"REFUSED: {refusal}")
    print()
    print("Now run `hermes plugins remove guide` to remove the plugin itself.")
    return 1 if report.refusals else 0
