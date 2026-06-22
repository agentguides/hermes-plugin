"""Scope-name derivation from $HERMES_HOME."""

from __future__ import annotations

from pathlib import Path

from guide_plugin.scope import DEFAULT_SCOPE_NAME, derive_scope


def test_default_profile_returns_default(tmp_path: Path, monkeypatch) -> None:
    # We have to mock ~/.hermes resolution against tmp_path because derive_scope
    # compares the resolved hermes_home against `~/.hermes`. We approximate by
    # passing the path directly and patching the resolved value.
    monkeypatch.setenv("HOME", str(tmp_path))
    default_home = tmp_path / ".hermes"
    default_home.mkdir()
    assert derive_scope(default_home) == DEFAULT_SCOPE_NAME


def test_named_profile_returns_basename(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".hermes" / "profiles" / "work").mkdir(parents=True)
    work = tmp_path / ".hermes" / "profiles" / "work"
    assert derive_scope(work) == "work"


def test_relocated_hermes_home_falls_back_to_basename(
    tmp_path: Path, monkeypatch
) -> None:
    """Operator with a non-standard $HERMES_HOME still gets a usable scope."""
    monkeypatch.setenv("HOME", str(tmp_path))
    custom = tmp_path / "elsewhere" / "team-hermes"
    custom.mkdir(parents=True)
    assert derive_scope(custom) == "team-hermes"


def test_env_var_drives_derivation_when_arg_absent(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".hermes" / "profiles" / "ops").mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes" / "profiles" / "ops"))
    assert derive_scope() == "ops"
