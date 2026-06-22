"""Read/write our cron entry in `$HERMES_HOME/cron/jobs.json`.

Hermes's cron feature persists every job to a single `cron/jobs.json` array
(not per-file). The plugin owns one named job, ``guide-sync``, that the
operator opts into via ``hermes cron resume guide-sync``.

The plugin's ``cron/guide-sync.json`` template is the documentation source
of truth for what we install. ``install()`` reads that template, runs
``${PLUGIN_ROOT}`` substitution against the active plugin install, and
upserts the resulting entry into ``jobs.json``. ``remove()`` strips our
entry by name. Every other entry in ``jobs.json`` survives both operations.
"""

from __future__ import annotations

import json
from pathlib import Path


JOB_NAME = "guide-sync"


def _atomic_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _load_jobs(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{path}: invalid JSON: {exc}") from exc
    if isinstance(data, list):
        return [j for j in data if isinstance(j, dict)]
    if isinstance(data, dict) and isinstance(data.get("jobs"), list):
        return [j for j in data["jobs"] if isinstance(j, dict)]
    raise RuntimeError(
        f"{path}: expected an array of job objects or {{\"jobs\": [...]}}"
    )


def _emit(path: Path, jobs: list[dict]) -> None:
    _atomic_write_json(path, jobs)


def render_entry(template: Path, plugin_root: Path) -> dict:
    """Load the on-disk template and substitute `${PLUGIN_ROOT}`."""
    raw = template.read_text(encoding="utf-8")
    rendered = raw.replace("${PLUGIN_ROOT}", str(plugin_root))
    data = json.loads(rendered)
    if not isinstance(data, dict) or data.get("name") != JOB_NAME:
        raise RuntimeError(
            f"{template}: malformed template (expected an object with name={JOB_NAME!r})"
        )
    return data


def install(jobs_json: Path, template: Path, plugin_root: Path) -> dict:
    """Upsert the `guide-sync` job in `cron/jobs.json`. Returns the entry."""
    entry = render_entry(template, plugin_root)
    jobs = _load_jobs(jobs_json)
    for i, j in enumerate(jobs):
        if j.get("name") == JOB_NAME:
            jobs[i] = entry
            _emit(jobs_json, jobs)
            return entry
    jobs.append(entry)
    _emit(jobs_json, jobs)
    return entry


def remove(jobs_json: Path) -> bool:
    """Strip the `guide-sync` entry from `cron/jobs.json`. Returns True if found."""
    if not jobs_json.is_file():
        return False
    jobs = _load_jobs(jobs_json)
    filtered = [j for j in jobs if j.get("name") != JOB_NAME]
    if len(filtered) == len(jobs):
        return False
    if filtered:
        _emit(jobs_json, filtered)
    else:
        # Don't leave an empty file around — easier to spot the absence.
        jobs_json.unlink()
    return True
