"""Regenerate this plugin's walk Skill triple from the runtime renderer.

The rendered `skills/{walk,walk-observer,walk-inline}/SKILL.md` files shipped in
this plugin tree are derived artifacts of `guide_cli.resources.render_*`. This
script makes the regen reproducible so the repo has a documented `just render`
step instead of manual copies.

The render spec below is the committed plugin's shape — verified byte-for-byte
against `skills/`. Note the deliberate observer=full / inline=low capability
split: that's the current committed state, reproduced here, not changed.

Usage:
    python scripts/render_plugin_skills.py            # this repo's skills/
    python scripts/render_plugin_skills.py <dir>...   # specific plugin checkouts
"""

from __future__ import annotations

import sys
from pathlib import Path

from guide_cli.resources import render_router_skill, render_walk_skill

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLUGINS = (REPO_ROOT,)

# dir-name -> rendered SKILL.md text. Spec matches the committed plugin tree.
SKILLS = {
    "walk": render_router_skill(default_mode="observer"),
    "walk-observer": render_walk_skill(
        mode="observer", capability="full", skill_name="walk-observer"
    ),
    "walk-inline": render_walk_skill(
        mode="inline", capability="low", skill_name="walk-inline"
    ),
}


def render_into(plugin_dir: Path) -> None:
    for name, text in SKILLS.items():
        target = plugin_dir / "skills" / name / "SKILL.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        rel = target.relative_to(REPO_ROOT) if target.is_relative_to(REPO_ROOT) else target
        print(f"  wrote {rel}")


def main(argv: list[str]) -> int:
    plugins = [Path(a) for a in argv] or list(DEFAULT_PLUGINS)
    for plugin_dir in plugins:
        if not plugin_dir.exists():
            print(f"error: plugin dir not found: {plugin_dir}", file=sys.stderr)
            return 1
        print(f"rendering walk Skill triple into {plugin_dir}/skills/")
        render_into(plugin_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
