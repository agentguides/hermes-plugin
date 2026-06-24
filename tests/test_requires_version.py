"""Compat-contract closure: the installed runtime satisfies the declared range.

`just verify-runtime` force-installs the built `agentguides` wheel and runs the
`requires_runtime` suite. This test reads the declared `requires.version` range
(the `agentguides>=…,<…` dev-group constraint in pyproject.toml — the plugin's
analogue of a Guide's `guide.runtime.requires.version`) and asserts the
runtime that is actually installed falls inside it — so a green verify-runtime
proves "plugin <this version> works with runtime <declared range>", rather than
merely "the plugin works against whatever wheel happened to build".
"""

from __future__ import annotations

import re
from importlib.metadata import version
from pathlib import Path

import pytest
from packaging.specifiers import SpecifierSet
from packaging.version import Version

pytestmark = pytest.mark.requires_runtime

ROOT = Path(__file__).resolve().parents[1]


def declared_runtime_range() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'"agentguides(?P<spec>[<>=!~][^"]*)"', text)
    assert m, "no `agentguides<spec>` constraint found in pyproject.toml dev group"
    return m.group("spec")


def test_installed_runtime_satisfies_declared_range() -> None:
    spec = SpecifierSet(declared_runtime_range())
    installed = Version(version("agentguides"))
    assert installed in spec, (
        f"installed agentguides {installed} does not satisfy declared requires.version {spec}"
    )
