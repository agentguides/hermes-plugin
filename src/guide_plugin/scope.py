"""Derive the *scope name* this plugin install represents.

Hermes does not document a `ctx.profile_name` API; the active profile is
identified entirely by `$HERMES_HOME`. The plan's rule:

- `$HERMES_HOME == ~/.hermes`            → scope = ``"default"``
- `$HERMES_HOME == ~/.hermes/profiles/X` → scope = basename = ``"X"``

Any other shape (an operator who relocated `~/.hermes` to a custom path)
falls back to the basename of `$HERMES_HOME`. We never raise — a working
scope name beats a broken plugin install.
"""

from __future__ import annotations

import os
from pathlib import Path


DEFAULT_SCOPE_NAME = "default"


def derive_scope(hermes_home: Path | None = None) -> str:
    """Return the scope name to tag walk records with."""
    hh = (hermes_home or Path(os.environ.get("HERMES_HOME") or "~/.hermes")).expanduser().resolve()
    home_root = Path(os.path.expanduser("~/.hermes")).resolve()
    if hh == home_root:
        return DEFAULT_SCOPE_NAME

    # Standard non-default shape: `<root>/profiles/<name>/`.
    if hh.parent.name == "profiles" and hh.parent.parent == home_root:
        return hh.name

    # Operator relocated the Hermes root (HERMES_HOME points somewhere
    # unexpected). Use the basename and roll with it — explicitly DON'T
    # raise: a working scope beats refusing to load.
    if hh.name and hh.name != ".":
        return hh.name
    return DEFAULT_SCOPE_NAME
