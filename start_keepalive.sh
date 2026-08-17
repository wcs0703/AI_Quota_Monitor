#!/usr/bin/env bash

# 定義路徑
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WORKSPACE_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
VENV_PYTHON="$WORKSPACE_DIR/.venv/bin/python"
mkdir -p "$SCRIPT_DIR/logs"

echo "══════════════════════════════════════════════════"
echo "🛡️  正在啟動 Gemini Model Quota 守護維持系統"
echo "══════════════════════════════════════════════════"

if [ -f "$VENV_PYTHON" ]; then
    PYTHON_CMD="$VENV_PYTHON"
elif command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

"$PYTHON_CMD" "$SCRIPT_DIR/quota_keepalive.py" "$@"
