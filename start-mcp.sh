#!/bin/bash
# Start MCP server — avoids uv lock contention between Claude Code sessions.
# First run: uv creates venv + installs deps.
# Subsequent runs: executes installed binary directly (no lock needed).
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
if [ -f ".venv/bin/gtm-mcp" ]; then
    exec .venv/bin/gtm-mcp
else
    exec uv run gtm-mcp
fi
