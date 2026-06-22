"""`profile.toml` schema mirror — what the operator's `.local/profile.toml` looks like.

The runtime view layer reads the same TOML shape from
`guide_cli.view.ViewConfig`; this module is the plugin-side authoring view of
the same schema. Keep the field set in lock-step.

Shape::

    policy = "all"
    include = []

    default_books  = ["db-ops"]            # IDs pulled on first-run
    default_guides = ["hello-walk"]
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]


Policy = Literal["all", "none", "include"]


@dataclass
class ProfileConfig:
    policy: Policy = "all"
    include: list[str] = field(default_factory=list)
    default_books: list[str] = field(default_factory=list)
    default_guides: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "ProfileConfig":
        if not path.is_file():
            return cls()
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        policy = data.get("policy", "all")
        if policy not in ("all", "none", "include"):
            raise ValueError(f"unknown policy {policy!r} in {path}")
        return cls(
            policy=policy,
            include=list(data.get("include") or []),
            default_books=list(data.get("default_books") or []),
            default_guides=list(data.get("default_guides") or []),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [f'policy = "{self.policy}"', "include = ["]
        for item in self.include:
            lines.append(f'  "{item}",')
        lines.append("]")
        lines.append("default_books = [")
        for item in self.default_books:
            lines.append(f'  "{item}",')
        lines.append("]")
        lines.append("default_guides = [")
        for item in self.default_guides:
            lines.append(f'  "{item}",')
        lines.append("]")
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        tmp.replace(path)
