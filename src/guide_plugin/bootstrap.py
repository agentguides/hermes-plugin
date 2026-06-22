"""First-run bootstrap for this plugin install (Plan §9).

Idempotent — re-running picks up where any previous run left off. The order
is deliberate: every step's failure mode leaves the next step recoverable.

  1. ``.local/`` + ``profile.toml`` (policy=all by default).
  2. ``.local/library-view/{books,guides}/`` empty dirs.
  3. ``$HERMES_HOME/cron/guide-sync.json`` symlink → plugin's template.
  4. Initial pull of default_books + default_guides from configured sources.
  5. ``guide view apply`` against the freshly-populated library.

Steps 4 and 5 shell out to `guide`; the earlier steps are pure filesystem
ops so they work even when `guide-cli` install failed and we want to leave
the bubble half-set-up for the operator to inspect.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import cli as _cli
from . import cron as _cron
from .paths import PluginPaths
from .profile_config import ProfileConfig


@dataclass
class BootstrapReport:
    """What changed during this first-run pass."""

    profile_created: bool = False
    view_dirs_created: bool = False
    cron_job_installed: bool = False
    pulled: list[str] = None  # type: ignore[assignment]
    pull_failures: list[tuple[str, str]] = None  # type: ignore[assignment]
    view_applied: bool = False

    def __post_init__(self) -> None:
        if self.pulled is None:
            self.pulled = []
        if self.pull_failures is None:
            self.pull_failures = []


def ensure_bubble(paths: PluginPaths, defaults: ProfileConfig) -> bool:
    """Step 1: create `.local/` and `profile.toml` if missing. Returns
    True when `profile.toml` was created fresh."""
    paths.bubble.mkdir(parents=True, exist_ok=True)
    if paths.profile_toml.is_file():
        return False
    defaults.save(paths.profile_toml)
    return True


def ensure_view_dirs(paths: PluginPaths) -> bool:
    """Step 2: empty `books/` + `guides/` subdirs of the library view."""
    fresh = not paths.view.exists()
    (paths.view / "books").mkdir(parents=True, exist_ok=True)
    (paths.view / "guides").mkdir(parents=True, exist_ok=True)
    return fresh


def ensure_cron_job(paths: PluginPaths) -> bool:
    """Step 3: upsert the `guide-sync` entry in `$HERMES_HOME/cron/jobs.json`.

    Hermes persists all cron jobs in one `cron/jobs.json` array; we own
    exactly one entry (`guide-sync`). Other entries are preserved. Returns
    True when the entry was newly added or refreshed."""
    paths.cron_dir.mkdir(parents=True, exist_ok=True)
    _cron.install(paths.cron_jobs_json, paths.cron_template, paths.plugin_root)
    return True


def initial_pull(
    paths: PluginPaths,
    config: ProfileConfig,
    report: BootstrapReport,
) -> None:
    """Step 4: pull default Books/Guides into `$GUIDE_HOME/library/`."""
    targets = [f"book:{b}" for b in config.default_books] + [
        f"guide:{g}" for g in config.default_guides
    ]
    if not targets:
        return
    if not _cli.guide_on_path():
        report.pull_failures.append(
            ("<all defaults>", "guide binary not on PATH; skipping initial pull")
        )
        return
    # IMPORTANT: bootstrap pulls into the MASTER library, not the view. We
    # override GUIDE_LIBRARY_PATH for this call so `guide sync` writes to
    # `$GUIDE_HOME/library/`. The view path is consumed by `apply_view()`
    # below, which symlinks from the master library into the view bubble.
    overlay = _cli.guide_env_overlay(
        guide_home=paths.guide_home,
        view_root=paths.master_lib,
        state_path=paths.state,
        scope="bootstrap",
    )
    for target in targets:
        try:
            res = _cli.run_guide(
                ["sync", target], env_overlay=overlay, check=False, capture=True
            )
        except Exception as exc:  # noqa: BLE001
            report.pull_failures.append((target, str(exc)))
            continue
        if res.returncode == 0:
            report.pulled.append(target)
        else:
            detail = (res.stderr or res.stdout or "").strip().splitlines()
            tail = " | ".join(detail[-3:]) if detail else "no output"
            report.pull_failures.append(
                (target, f"exit={res.returncode}: {tail}")
            )


def apply_view(paths: PluginPaths, report: BootstrapReport) -> None:
    """Step 5: re-apply the view's symlink farm against the master library."""
    if not _cli.guide_on_path():
        return
    # Use master_lib as GUIDE_LIBRARY_PATH so any list_library() done by
    # `view apply` for resolve_entries reads from the correct root. `--library`
    # is explicit but the env stays consistent for any sub-calls.
    overlay = _cli.guide_env_overlay(
        guide_home=paths.guide_home,
        view_root=paths.master_lib,
        state_path=paths.state,
        scope="bootstrap",
    )
    res = _cli.run_guide(
        ["view", "apply", str(paths.view), "--library", str(paths.master_lib)],
        env_overlay=overlay,
        check=False,
        capture=True,
    )
    report.view_applied = res.returncode == 0


def run(
    paths: PluginPaths,
    *,
    defaults: ProfileConfig | None = None,
) -> BootstrapReport:
    """Run every bootstrap step in order. Safe to re-run."""
    report = BootstrapReport()
    cfg_defaults = defaults or ProfileConfig()
    report.profile_created = ensure_bubble(paths, cfg_defaults)
    report.view_dirs_created = ensure_view_dirs(paths)
    report.cron_job_installed = ensure_cron_job(paths)

    # Load the actual config (may have been authored between runs).
    active = ProfileConfig.load(paths.profile_toml)
    initial_pull(paths, active, report)
    apply_view(paths, report)
    return report
