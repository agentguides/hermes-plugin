#!/usr/bin/env bash
# Hermes MCP server wrapper for the `guide` plugin.
#
# Hermes spawns this script per the `mcp_servers.guide.command` entry in
# `$HERMES_HOME/config.yaml`. The plugin's `register(ctx)` writes both the
# command path and the env: block, but Hermes does not always propagate
# the env: block all the way through (depends on host version), so this
# wrapper ALSO sources its env from the active plugin install's `.local/`
# state. That makes the wrapper robust to operators editing the env: block
# manually, and lets the env stay in sync with the per-profile policy.
#
# Resolution rule:
#   - HERMES_HOME is honored if already set; otherwise default to ~/.hermes.
#   - GUIDE_HOME defaults to ~/.guide.
#   - Per-profile overlay file (optional): $BUBBLE/env.sh — if present,
#     sourced LAST so it wins over the defaults. The plugin doesn't write
#     this file today, but operators are free to.
set -euo pipefail

: "${HERMES_HOME:=$HOME/.hermes}"
: "${GUIDE_HOME:=$HOME/.guide}"

PLUGIN_ROOT="$HERMES_HOME/plugins/guide"
BUBBLE="$PLUGIN_ROOT/.local"
VIEW="$BUBBLE/library-view"

# Scope name derivation mirrors guide_plugin.scope.derive_scope:
#   $HERMES_HOME == ~/.hermes              → default
#   $HERMES_HOME == ~/.hermes/profiles/X   → X
#   anything else                          → basename($HERMES_HOME)
DEFAULT_HOME="$HOME/.hermes"
if [ "$HERMES_HOME" = "$DEFAULT_HOME" ]; then
  SCOPE="default"
elif [ "$(dirname "$HERMES_HOME")" = "$DEFAULT_HOME/profiles" ]; then
  SCOPE="$(basename "$HERMES_HOME")"
else
  SCOPE="$(basename "$HERMES_HOME")"
fi

export GUIDE_HOME
export GUIDE_LIBRARY_PATH="$VIEW"
export GUIDE_STATE_PATH="$GUIDE_HOME/state"
export GUIDE_HARNESS="hermes"
export GUIDE_SCOPE="$SCOPE"

# Operator-authored overlay last so it wins.
if [ -f "$BUBBLE/env.sh" ]; then
  # shellcheck disable=SC1090,SC1091
  . "$BUBBLE/env.sh"
fi

exec guide mcp
