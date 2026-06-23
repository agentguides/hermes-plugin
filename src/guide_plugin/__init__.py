"""Internal helpers for the Hermes `guide` plugin.

The plugin is intentionally self-contained — it never imports from
``guide_cli``. Once `agentguides` is installed via `uv tool install agentguides`
(or equivalent), the plugin shells out to the `guide` binary on PATH for
all runtime operations. This way the plugin and runtime can ship from
separate repos with independent release cadences.
"""

__version__ = "0.5.5"
