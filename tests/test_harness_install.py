"""Harness-install proof: the Hermes `guide` integration installs into a real
Hermes home via the runtime's OWN packaged installer (`agentguides.setup`).

`guide setup hermes` provisions two things this test asserts end-to-end:

  1. the walk Skill triple under `<hermes>/skills/{walk,walk-observer,walk-inline}/`,
  2. the `mcp_servers.guide` registration in `<hermes>/config.yaml`.

We point `AG_HERMES_HOME` at a throwaway dir (the runtime resolves the hermes
root from that env var) and pre-seed an empty `config.yaml` — the runtime's
McpServerEntryComponent only writes the `mcp_servers.guide` entry when a hermes
`config.yaml` already exists (otherwise hermes isn't installed yet and the entry
is deferred). This mirrors `test_multi_profile.py`'s install path (which exercises
the plugin's own `mcp_config.install`) but proves it through the runtime installer
that operators actually run.

Marked `requires_runtime` and gated by `importorskip("agentguides.setup")` so the
runtime-source-free core suite (`pytest -m "not requires_runtime"`) stays green.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytest.importorskip("agentguides.setup")

from agentguides.setup import (  # noqa: E402
    HarnessState,
    InstallStatus,
    setup,
    verify_setup,
)


@pytest.mark.requires_runtime
def test_hermes_setup_registers_mcp_server_and_walk_skills(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hermes_home = tmp_path / "hermes-home"
    hermes_home.mkdir()
    # Pre-seed an empty config.yaml so the mcp_servers.guide entry lands (the
    # installer defers it when hermes isn't installed yet).
    (hermes_home / "config.yaml").write_text("", encoding="utf-8")
    monkeypatch.setenv("AG_HERMES_HOME", str(hermes_home))

    state = HarnessState.resolve("hermes")
    report = setup(state)
    assert not report.failures, f"setup reported failures: {report.failures}"

    # 1) Walk Skill triple present.
    for name in ("walk", "walk-observer", "walk-inline"):
        skill = hermes_home / "skills" / name / "SKILL.md"
        assert skill.is_file(), f"walk skill not installed: {skill}"

    # 2) mcp_servers.guide registered in the profile config.
    cfg = yaml.safe_load((hermes_home / "config.yaml").read_text(encoding="utf-8")) or {}
    assert "guide" in (cfg.get("mcp_servers") or {}), (
        f"mcp_servers.guide not registered; config={cfg}"
    )

    # 3) The runtime's own verifier reports a clean install.
    verify = verify_setup(state)
    assert all(s.status is InstallStatus.OK for s in verify.statuses), (
        f"verify_setup not clean: {[(s.component_name, s.status) for s in verify.statuses]}"
    )
