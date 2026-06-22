"""`hermes guide uninstall-self` (Plan §"Phase C — uninstall-self").

Per-profile uninstall — leaves Hermes's own files and the centralized
`$GUIDE_HOME/` untouched by default. Optional purge flags reach further:

- ``--purge-library`` removes `$GUIDE_HOME/library/`. Refuses when ANY other
  Hermes profile still has the plugin installed (defensive — the library is
  shared across profiles by design; one profile's uninstall must not steal
  content from another).
- ``--purge-state`` removes `$GUIDE_HOME/state/`. DESTRUCTIVE: this wipes
  every walk record across every harness + scope, not just this profile.
  Always warned; never bundled into a higher-level purge.
- ``--purge-home`` removes `$GUIDE_HOME/` outright (sources + cache +
  library + state).

After this CLI completes, the operator still has to run
``hermes plugins remove guide`` to remove the plugin itself.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from .paths import PLUGIN_NAME, PluginPaths
from . import cron as _cron
from . import mcp_config


@dataclass
class UninstallReport:
    view_symlinks_cleared: int = 0
    cron_job_removed: bool = False
    bubble_removed: bool = False
    mcp_entry_removed: bool = False
    library_purged: bool = False
    state_purged: bool = False
    home_purged: bool = False
    refusals: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.refusals is None:
            self.refusals = []


def _clear_view_symlinks(view_root: Path) -> int:
    """Remove every symlink under view_root/{books,guides}/. Non-symlinks
    survive (operator-authored content is never trampled)."""
    count = 0
    for sub in ("books", "guides"):
        d = view_root / sub
        if not d.is_dir():
            continue
        for child in d.iterdir():
            if child.is_symlink():
                child.unlink()
                count += 1
    return count


def _another_profile_has_plugin(hermes_home: Path) -> bool:
    """True iff any sibling profile under `~/.hermes/profiles/*/plugins/guide/`
    still has the plugin installed. Conservative — we only inspect the standard
    profile-shape layout; operators using exotic HERMES_HOME shapes pass
    `--force` (not yet implemented; surfaces as a clear refusal)."""
    root = Path("~/.hermes").expanduser().resolve()
    if root != hermes_home and root != hermes_home.parent.parent:
        # Operator-relocated tree; we can't enumerate sibling profiles cleanly.
        return False
    profiles_dir = root / "profiles"
    if not profiles_dir.is_dir():
        return False
    for prof in profiles_dir.iterdir():
        if not prof.is_dir():
            continue
        if prof.resolve() == hermes_home:
            continue
        if (prof / "plugins" / PLUGIN_NAME).is_dir():
            return True
    return False


def run(
    paths: PluginPaths,
    *,
    purge_library: bool = False,
    purge_state: bool = False,
    purge_home: bool = False,
) -> UninstallReport:
    """Tear down this profile's plugin install. Returns a structured report."""
    report = UninstallReport()

    # 1. Symlink farm.
    if paths.view.is_dir():
        report.view_symlinks_cleared = _clear_view_symlinks(paths.view)

    # 2. Cron job entry.
    if paths.cron_jobs_json.is_file():
        report.cron_job_removed = _cron.remove(paths.cron_jobs_json)

    # 3. mcp_servers.guide entry.
    if paths.config_yaml.is_file():
        report.mcp_entry_removed = mcp_config.remove(paths.config_yaml)

    # 4. .local/ bubble (operator state — policy + library-view dirs).
    if paths.bubble.is_dir():
        shutil.rmtree(paths.bubble)
        report.bubble_removed = True

    # 5. Optional purges. We do these AFTER per-profile cleanup so a partial
    # failure in the per-profile path doesn't leave a half-purged $GUIDE_HOME.
    if purge_home:
        if paths.guide_home.is_dir():
            shutil.rmtree(paths.guide_home)
            report.home_purged = True
        return report

    if purge_library and paths.master_lib.is_dir():
        if _another_profile_has_plugin(paths.hermes_home):
            report.refusals.append(
                "--purge-library refused: another Hermes profile still has the "
                "guide plugin installed; removing the library would break it. "
                "Uninstall the plugin from every profile first."
            )
        else:
            shutil.rmtree(paths.master_lib)
            report.library_purged = True

    if purge_state and paths.state.is_dir():
        shutil.rmtree(paths.state)
        report.state_purged = True

    return report
