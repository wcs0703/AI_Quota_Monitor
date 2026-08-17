#!/bin/bash

# Define paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WORKSPACE_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
VENV_PYTHON="$WORKSPACE_DIR/.venv/bin/python"
mkdir -p "$SCRIPT_DIR/logs"

echo "══════════════════════════════════════════════════"
echo "🤖 正在啟動 Gemini API 使用狀況監控儀表板 (Streamlit)"
echo "══════════════════════════════════════════════════"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ 找不到虛擬環境: $VENV_PYTHON"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: 找不到虛擬環境 $VENV_PYTHON" >> "$SCRIPT_DIR/logs/error.log"
    exit 1
fi

"$VENV_PYTHON" -m streamlit run "$SCRIPT_DIR/app_monitor.py" --server.port 8502 --server.address localhost
