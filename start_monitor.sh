#!/bin/bash

# Define paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WORKSPACE_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
if [ -f "$WORKSPACE_DIR/.venv/bin/python" ]; then
    VENV_PYTHON="$WORKSPACE_DIR/.venv/bin/python"
elif [ -f "$WORKSPACE_DIR/.venv/Scripts/python.exe" ]; then
    VENV_PYTHON="$WORKSPACE_DIR/.venv/Scripts/python.exe"
else
    VENV_PYTHON="python"
fi

"$VENV_PYTHON" "$SCRIPT_DIR/start_monitor.py" "$@"
