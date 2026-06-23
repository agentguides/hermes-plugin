"""Helpers for shelling out to `guide`.

The plugin owns no state itself — every runtime operation routes through
the `guide` binary on PATH. This module is the thin subprocess wrapper.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Sequence


class GuideNotInstalled(RuntimeError):
    """Raised when `guide` is missing AND we can't auto-install it."""


def guide_on_path() -> bool:
    return shutil.which("guide") is not None


def uv_on_path() -> bool:
    return shutil.which("uv") is not None


def ensure_guide_installed() -> None:
    """Plan §1: if `guide` is missing, try `uv tool install guide-cli`.

    Falls through to a clear operator-facing error if `uv` is also absent.
    """
    if guide_on_path():
        return
    if not uv_on_path():
        raise GuideNotInstalled(
            "guide-cli is not installed and `uv` is not available to "
            "auto-install it. Install one of:\n"
            "  pipx install agentguides   (or)   uv tool install agentguides\n"
            "then re-enable the plugin."
        )
    subprocess.run(
        ["uv", "tool", "install", "agentguides"],
        check=True,
        env=os.environ.copy(),
    )
    if not guide_on_path():
        raise GuideNotInstalled(
            "`uv tool install agentguides` reported success but `guide` is "
            "still not on PATH. Ensure `~/.local/bin` (or your uv tool "
            "install dir) is on PATH."
        )


def run_guide(
    args: Sequence[str],
    *,
    env_overlay: dict[str, str] | None = None,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess:
    """Run `guide <args>` with the current env plus an optional overlay."""
    env = os.environ.copy()
    if env_overlay:
        env.update(env_overlay)
    return subprocess.run(
        ["guide", *args],
        check=check,
        env=env,
        capture_output=capture,
        text=True,
    )


def guide_env_overlay(
    *,
    guide_home: Path,
    view_root: Path,
    state_path: Path,
    scope: str,
) -> dict[str, str]:
    """The standard GUIDE_* env block the plugin imposes on every shellout."""
    return {
        "GUIDE_HOME": str(guide_home),
        "GUIDE_LIBRARY_PATH": str(view_root),
        "GUIDE_STATE_PATH": str(state_path),
        "GUIDE_HARNESS": "hermes",
        "GUIDE_SCOPE": scope,
    }
