#!/usr/bin/env bash
# Hermes MCP server wrapper for the `guide` plugin.
#
# Dumb exec stub — every GUIDE_* env var the MCP server needs is set by
# Hermes from the `mcp_servers.guide.env` block in `$HERMES_HOME/config.yaml`,
# which `register(ctx)` writes through `guide_plugin.mcp_config.install()`.
# Verified live during M3 validation: tagging (`harness=hermes`, `scope=...`)
# propagates correctly without any wrapper-side derivation. See plugin README
# + the v0.5.5 plan §"Phase C".
#
# The wrapper file still exists (rather than putting `command: guide` directly
# in config.yaml) because operators expect `command:` to point at a stable
# file inside the plugin tree — easier to introspect, version-tag, and
# replace per-profile if anyone ever needs a per-profile env overlay.

set -euo pipefail
exec guide mcp
