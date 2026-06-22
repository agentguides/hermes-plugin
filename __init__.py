"""Hermes plugin entrypoint — `register(ctx)`.

Plan §"Phase C — register(ctx)":

  1. Detect `guide` on PATH; auto-`uv tool install guide-cli` if missing.
  2. Read `$HERMES_HOME` → derive scope name.
  3. Compute paths.
  4. Render / register the walk Skills.
  5. Register MCP server via `$HERMES_HOME/config.yaml` (Hermes has no
     `register_mcp_server` API).
  6. Register CLI subcommands (`hermes guide …`).
  7. Register slash `/sync`.
  8. Register `on_session_start` hook for background auto-sync.
  9. Run first-run bootstrap for this profile install.
 10. Post onboarding hint.

Hermes calls `register(ctx)` once per process boot. We keep the body
defensive: any single step failing logs and continues so the operator
can recover the bubble manually if `guide-cli` isn't installable in
their environment.

The package layout in this repo:

    plugins/hermes-plugin/
      __init__.py                 ← THIS file (Hermes's entry point)
      src/guide_plugin/           ← internal lib (importable as `guide_plugin`)

When Hermes loads the plugin it adds the plugin root to `sys.path`, which
makes `src/` importable. To stay portable to a standalone repo, the helper
modules expose their public API via `guide_plugin.<module>`.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path


_PLUGIN_DIR = Path(__file__).resolve().parent
_SRC = _PLUGIN_DIR / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def _log(message: str) -> None:
    """Single emission point — easy to swap for Hermes's logger."""
    print(f"[guide-plugin] {message}", file=sys.stderr)


def register(ctx) -> None:  # noqa: D401 — Hermes contract
    """Hermes plugin entry point. Returns nothing."""
    try:
        _do_register(ctx)
    except Exception as exc:  # noqa: BLE001
        # Refuse to fail loud — Hermes shouldn't be unable to boot
        # because the plugin tripped on a config file.
        _log(f"plugin load failed: {exc}")
        traceback.print_exc()


def _do_register(ctx) -> None:
    from guide_plugin import bootstrap as _bootstrap
    from guide_plugin import cli as _cli
    from guide_plugin import handlers as _handlers
    from guide_plugin import mcp_config
    from guide_plugin.paths import compute
    from guide_plugin.profile_config import ProfileConfig
    from guide_plugin.scope import derive_scope

    paths = compute()
    scope = derive_scope(paths.hermes_home)
    _log(f"loading: hermes_home={paths.hermes_home} scope={scope!r}")

    # 1. Ensure `guide` is on PATH.
    try:
        _cli.ensure_guide_installed()
    except _cli.GuideNotInstalled as exc:
        _log(str(exc))
        # We still continue — surfacing the failure via /sync is more useful
        # than refusing to load.

    # 4. Walk Skills — register each `SKILL.md` from the plugin's skills/ dir.
    skills_dir = paths.plugin_root / "skills"
    if skills_dir.is_dir():
        for child in sorted(skills_dir.iterdir()):
            skill_md = child / "SKILL.md"
            if skill_md.is_file() and hasattr(ctx, "register_skill"):
                try:
                    ctx.register_skill(name=child.name, path=str(skill_md))
                except Exception as exc:  # noqa: BLE001
                    _log(f"register_skill({child.name!r}) failed: {exc}")

    # 5. MCP server registration via config.yaml mutation.
    try:
        mcp_config.install(
            paths.config_yaml,
            wrapper_script=paths.wrapper_script,
            guide_home=paths.guide_home,
            view_root=paths.view,
            state_path=paths.state,
            scope=scope,
        )
    except Exception as exc:  # noqa: BLE001
        _log(f"failed to wire mcp_servers.guide into {paths.config_yaml}: {exc}")

    # 6. CLI subcommands — `hermes guide <verb>`.
    if hasattr(ctx, "register_cli_command"):
        _register_cli_commands(ctx, paths)

    # 7. Slash command — `/sync` in CLI sessions.
    if hasattr(ctx, "register_command"):
        ctx.register_command(
            name="sync",
            handler=lambda args: _slash_sync(paths),
            description="Refresh the guide library and re-apply this profile's view.",
        )

    # 8. on_session_start hook — best-effort background auto-sync.
    if hasattr(ctx, "register_hook"):
        ctx.register_hook("on_session_start", lambda **kw: _maybe_auto_sync(paths))

    # 9. First-run bootstrap for this profile install. Idempotent.
    try:
        defaults = ProfileConfig(
            policy="all",
            default_books=[],
            default_guides=[],
        )
        report = _bootstrap.run(paths, defaults=defaults)
        if report.profile_created:
            _log(f"first-run: created {paths.profile_toml}")
        if report.pull_failures:
            for entry, err in report.pull_failures:
                _log(f"first-run pull failed: {entry} — {err}")
    except Exception as exc:  # noqa: BLE001
        _log(f"bootstrap failed: {exc}")

    # 10. Onboarding hint — only on a genuinely fresh install.
    if not paths.profile_toml.is_file():
        _log(
            "Auto-sync cron is installed but paused. "
            "Run `hermes cron resume guide-sync` to enable it."
        )


def _register_cli_commands(ctx, paths) -> None:
    """Wire up `hermes guide {pull,install,list,sync,status,profile,uninstall-self}`."""
    from guide_plugin import handlers as _h

    def _wrap(fn, *static_args):
        def runner(args):
            return fn(paths, *static_args, *list(args) if args else [])
        return runner

    ctx.register_cli_command(
        name="list",
        help="List entries currently in this profile's view.",
        setup_fn=lambda: None,
        handler_fn=lambda args: _h.list_view(paths, args),
    )
    ctx.register_cli_command(
        name="pull",
        help="Pull a Book/Guide into the centralized library.",
        setup_fn=lambda: None,
        handler_fn=lambda args: _h.pull(paths, args[0]) if args else _exit_2(
            "pull requires an id"
        ),
    )
    ctx.register_cli_command(
        name="install",
        help="Pull a Book/Guide and add it to this profile's view.",
        setup_fn=lambda: None,
        handler_fn=lambda args: _h.install(paths, args[0]) if args else _exit_2(
            "install requires an id"
        ),
    )
    ctx.register_cli_command(
        name="sync",
        help="Refresh every entry in the library and re-apply the view.",
        setup_fn=lambda: None,
        handler_fn=lambda args: _h.sync(paths, args),
    )
    ctx.register_cli_command(
        name="status",
        help="One-shot health summary for this plugin install.",
        setup_fn=lambda: None,
        handler_fn=lambda args: _h.status(paths, args),
    )
    ctx.register_cli_command(
        name="profile",
        help="Per-profile config: `policy <all|none|include>` or `include <kind:id>`.",
        setup_fn=lambda: None,
        handler_fn=lambda args: _profile_router(paths, args),
    )
    ctx.register_cli_command(
        name="uninstall-self",
        help="Remove this profile's plugin install (optionally with --purge-*).",
        setup_fn=lambda: None,
        handler_fn=lambda args: _uninstall_router(paths, args),
    )


def _profile_router(paths, args: list[str] | None) -> int:
    from guide_plugin import handlers as _h

    if not args or len(args) < 2:
        print(
            "usage: hermes guide profile policy <all|none|include>\n"
            "   or: hermes guide profile include <kind:id>"
        )
        return 2
    verb, value = args[0], args[1]
    if verb == "policy":
        return _h.profile_policy(paths, value)
    if verb == "include":
        return _h.profile_include(paths, value)
    print(f"unknown profile verb {verb!r}")
    return 2


def _uninstall_router(paths, args: list[str] | None) -> int:
    from guide_plugin import handlers as _h

    flags = set(args or [])
    return _h.uninstall_self(
        paths,
        purge_library="--purge-library" in flags,
        purge_state="--purge-state" in flags,
        purge_home="--purge-home" in flags,
    )


def _slash_sync(paths) -> str:
    from guide_plugin import handlers as _h

    rc = _h.sync(paths)
    return "sync OK" if rc == 0 else f"sync exited {rc}; see logs"


def _maybe_auto_sync(paths) -> None:
    """Hook stub — the cron job is the real auto-sync. This is a place to
    hang lightweight on-session warmups if we want them later."""
    # No-op by default. The plan calls for auto_sync via cron, which is
    # already installed (paused). Operators opt-in via
    # `hermes cron resume guide-sync`.
    return None


def _exit_2(msg: str) -> int:
    print(f"error: {msg}")
    return 2
