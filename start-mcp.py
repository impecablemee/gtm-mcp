#!/usr/bin/env python3
"""Start MCP server — avoids uv lock contention between Claude Code sessions.

First run: uv creates venv + installs deps.
Subsequent runs: executes installed binary directly (no lock needed).
Works on macOS, Linux, and Windows.
"""
import os, sys, subprocess
from pathlib import Path

root = Path(__file__).parent
os.chdir(root)

# Check for installed binary (venv already created by first uv run)
if sys.platform == "win32":
    binary = root / ".venv" / "Scripts" / "gtm-mcp.exe"
else:
    binary = root / ".venv" / "bin" / "gtm-mcp"

if binary.exists():
    os.execv(str(binary), [str(binary)])
else:
    # First run — uv creates venv + installs
    os.execvp("uv", ["uv", "run", "gtm-mcp"])
