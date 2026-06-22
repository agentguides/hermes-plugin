"""`mcp_servers.guide` install/remove round-trip against config.yaml."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from guide_plugin import mcp_config


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_install_into_empty_config_creates_servers_block(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    entry = mcp_config.install(
        cfg,
        wrapper_script=tmp_path / "wrapper.sh",
        guide_home=tmp_path / "guide",
        view_root=tmp_path / "view",
        state_path=tmp_path / "state",
        scope="default",
    )
    assert entry["command"] == str(tmp_path / "wrapper.sh")
    assert entry["env"]["GUIDE_SCOPE"] == "default"
    on_disk = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    assert "guide" in on_disk["mcp_servers"]


def test_install_preserves_other_servers(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    _write_yaml(cfg, {
        "mcp_servers": {"other": {"command": "/usr/bin/other-mcp"}},
        "model": {"provider": "anthropic"},
    })
    mcp_config.install(
        cfg,
        wrapper_script=tmp_path / "w.sh",
        guide_home=tmp_path / "guide",
        view_root=tmp_path / "view",
        state_path=tmp_path / "state",
        scope="work",
    )
    on_disk = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    assert on_disk["mcp_servers"]["other"]["command"] == "/usr/bin/other-mcp"
    assert on_disk["mcp_servers"]["guide"]["env"]["GUIDE_SCOPE"] == "work"
    assert on_disk["model"]["provider"] == "anthropic"


def test_install_is_idempotent(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    for _ in range(3):
        mcp_config.install(
            cfg,
            wrapper_script=tmp_path / "w.sh",
            guide_home=tmp_path / "guide",
            view_root=tmp_path / "view",
            state_path=tmp_path / "state",
            scope="default",
        )
    on_disk = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    # Still one entry, not three.
    assert list(on_disk["mcp_servers"].keys()) == ["guide"]


def test_remove_strips_guide_only(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    _write_yaml(cfg, {
        "mcp_servers": {
            "other": {"command": "/usr/bin/other-mcp"},
            "guide": {"command": "/x"},
        }
    })
    removed = mcp_config.remove(cfg)
    assert removed is True
    on_disk = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    assert "guide" not in on_disk["mcp_servers"]
    assert "other" in on_disk["mcp_servers"]


def test_remove_collapses_empty_mcp_servers_block(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    _write_yaml(cfg, {"mcp_servers": {"guide": {"command": "/x"}}})
    mcp_config.remove(cfg)
    on_disk = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    assert "mcp_servers" not in (on_disk or {})


def test_remove_no_op_when_missing(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    _write_yaml(cfg, {"model": {"provider": "anthropic"}})
    removed = mcp_config.remove(cfg)
    assert removed is False


def test_install_rejects_non_yaml(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text("not: [yaml: at all", encoding="utf-8")
    with pytest.raises(RuntimeError, match="invalid YAML"):
        mcp_config.install(
            cfg,
            wrapper_script=tmp_path / "w.sh",
            guide_home=tmp_path / "g",
            view_root=tmp_path / "v",
            state_path=tmp_path / "s",
            scope="x",
        )
