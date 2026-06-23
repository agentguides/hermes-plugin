"""Release consistency for the hermes-plugin: manifest, pyproject, and CHANGELOG agree.

The plugin's canonical version source is its MANIFEST (`plugin.yaml` `version`).
This script asserts:

  (a) the pyproject `[project].version` equals the manifest version, and
  (b) a `## [<version>]` heading exists in CHANGELOG.md.

With an optional CLI arg it also asserts the manifest version equals that arg
and that the git tag `v<version>` is free (release-gate use).

Usage:
    python scripts/check_version_changelog.py           # current version is consistent + has a CHANGELOG entry
    python scripts/check_version_changelog.py 0.5.6     # also assert version == 0.5.6 and tag v0.5.6 is free

Used by `just build` / `just release-dryrun` / `just tag` and the pre-commit hook.
Versions are read with regexes (no tomllib / yaml dep) so this runs cleanly on Python 3.10+.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "plugin.yaml"
CHANGELOG = ROOT / "CHANGELOG.md"


def manifest_version() -> str:
    text = MANIFEST.read_text(encoding="utf-8")
    # version: "0.5.5"  (quoted or bare)
    m = re.search(r'(?m)^version\s*:\s*["\']?([^"\'\s]+)["\']?\s*$', text)
    if not m:
        raise SystemExit(f"could not find a version in {MANIFEST.relative_to(ROOT)}")
    return m.group(1)


def pyproject_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    if not m:
        raise SystemExit("could not find a version in pyproject.toml")
    return m.group(1)


def changelog_has(version: str) -> bool:
    text = CHANGELOG.read_text(encoding="utf-8")
    return re.search(rf"(?m)^##\s*\[{re.escape(version)}\]", text) is not None


def tag_exists(version: str) -> bool:
    out = subprocess.run(
        ["git", "tag", "--list", f"v{version}"],
        cwd=ROOT, capture_output=True, text=True,
    )
    return bool(out.stdout.strip())


def main(argv: list[str]) -> int:
    version = manifest_version()
    expected = argv[1] if len(argv) > 1 and argv[1] else None

    errors = []
    pyproj = pyproject_version()
    if pyproj != version:
        errors.append(f"pyproject version {pyproj} != manifest version {version}")
    if expected and expected != version:
        errors.append(f"manifest version {version} != requested {expected}")
    if not changelog_has(version):
        errors.append(f"no '## [{version}]' heading in {CHANGELOG.relative_to(ROOT)}")
    if expected and tag_exists(version):
        errors.append(f"tag v{version} already exists")

    if errors:
        print("version/CHANGELOG check FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1
    suffix = f", tag v{version} free" if expected else ""
    print(f"OK: manifest=pyproject={version} has a CHANGELOG entry{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
