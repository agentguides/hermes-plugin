"""Make `guide_plugin` importable when pytest collects this directory.

The plugin lives at `<repo>/plugins/hermes-plugin/src/guide_plugin/`. Until
we extract the plugin to its own repo (with its own pyproject.toml), pytest
needs help finding the import root. Once extracted, the plugin will be
installed editable (`pip install -e .`) and this conftest disappears.
"""

from __future__ import annotations

import sys
from pathlib import Path


_PLUGIN_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_PLUGIN_SRC) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_SRC))
