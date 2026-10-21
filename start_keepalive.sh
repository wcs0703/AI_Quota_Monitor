#!/usr/bin/env bash

# 定義路徑
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WORKSPACE_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
VENV_PYTHON="$WORKSPACE_DIR/.venv/bin/python"
mkdir -p "$SCRIPT_DIR/logs"

if [ -f "$WORKSPACE_DIR/.venv/bin/python" ]; then
    PYTHON_CMD="$WORKSPACE_DIR/.venv/bin/python"
elif [ -f "$WORKSPACE_DIR/.venv/Scripts/python.exe" ]; then
    PYTHON_CMD="$WORKSPACE_DIR/.venv/Scripts/python.exe"
elif command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

"$PYTHON_CMD" "$SCRIPT_DIR/start_keepalive.py" "$@"

