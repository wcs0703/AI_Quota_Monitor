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

if [[ "$OSTYPE" == "darwin"* ]]; then
    (sleep 1.5 && open "http://localhost:8502") &
fi

"$VENV_PYTHON" -m streamlit run "$SCRIPT_DIR/app_monitor.py" --server.port 8502 --server.address localhost --server.headless false
