"""Cron job install/remove against `$HERMES_HOME/cron/jobs.json`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from guide_plugin import cron


REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = REPO_ROOT / "plugins" / "hermes-plugin" / "cron" / "guide-sync.json"


def test_install_adds_job_to_empty_file(tmp_path: Path) -> None:
    jobs_json = tmp_path / "cron" / "jobs.json"
    plugin_root = tmp_path / "plugins" / "guide"
    plugin_root.mkdir(parents=True)
    entry = cron.install(jobs_json, TEMPLATE, plugin_root)
    assert entry["name"] == "guide-sync"
    # ${PLUGIN_ROOT} substitution.
    assert str(plugin_root) in entry["script"]
    on_disk = json.loads(jobs_json.read_text(encoding="utf-8"))
    assert isinstance(on_disk, list) and len(on_disk) == 1
    assert on_disk[0]["name"] == "guide-sync"


def test_install_preserves_other_jobs(tmp_path: Path) -> None:
    jobs_json = tmp_path / "cron" / "jobs.json"
    jobs_json.parent.mkdir(parents=True)
    jobs_json.write_text(
        json.dumps([{"name": "other-job", "schedule": "@daily"}]), encoding="utf-8"
    )
    cron.install(jobs_json, TEMPLATE, tmp_path / "plugin")
    on_disk = json.loads(jobs_json.read_text(encoding="utf-8"))
    names = sorted(j["name"] for j in on_disk)
    assert names == ["guide-sync", "other-job"]


def test_install_is_idempotent(tmp_path: Path) -> None:
    jobs_json = tmp_path / "cron" / "jobs.json"
    for _ in range(3):
        cron.install(jobs_json, TEMPLATE, tmp_path / "plugin")
    on_disk = json.loads(jobs_json.read_text(encoding="utf-8"))
    assert [j["name"] for j in on_disk] == ["guide-sync"]


def test_remove_strips_only_guide_sync(tmp_path: Path) -> None:
    jobs_json = tmp_path / "cron" / "jobs.json"
    jobs_json.parent.mkdir(parents=True)
    jobs_json.write_text(
        json.dumps([
            {"name": "guide-sync", "schedule": "0 * * * *"},
            {"name": "other-job", "schedule": "@daily"},
        ]),
        encoding="utf-8",
    )
    assert cron.remove(jobs_json) is True
    on_disk = json.loads(jobs_json.read_text(encoding="utf-8"))
    assert [j["name"] for j in on_disk] == ["other-job"]


def test_remove_deletes_file_when_no_jobs_remain(tmp_path: Path) -> None:
    jobs_json = tmp_path / "cron" / "jobs.json"
    jobs_json.parent.mkdir(parents=True)
    jobs_json.write_text(
        json.dumps([{"name": "guide-sync", "schedule": "0 * * * *"}]),
        encoding="utf-8",
    )
    cron.remove(jobs_json)
    assert not jobs_json.exists()


def test_remove_no_op_when_absent(tmp_path: Path) -> None:
    jobs_json = tmp_path / "cron" / "jobs.json"
    assert cron.remove(jobs_json) is False
