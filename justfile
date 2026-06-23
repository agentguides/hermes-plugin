# agentguides/hermes-plugin — task runner

# List available recipes.
default:
    @just --list

# Run the test suite (editable-installs guide_plugin + sibling guide-cli).
test:
    uv run pytest

# Regenerate the walk Skill triple from the guide-cli renderer.
render:
    uv run python scripts/render_plugin_skills.py
