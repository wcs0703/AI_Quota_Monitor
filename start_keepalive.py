#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
start_keepalive.py
=============================================================================
跨平台 Gemini Model Quota 守護維持系統啟動腳本 (macOS / Windows / Linux 通用)

功能說明：
1. 跨平台自動偵測工作區虛擬環境 (.venv)，優先使用專案虛擬環境之 Python 直譯器。
2. 自動建立 logs/ 日誌記錄目錄。
3. 完整轉發所有命令列參數至 quota_keepalive.py (例如 --once, --hours 等)。
4. 處理終端機中斷訊號與編碼容錯。

使用方式：
    python start_keepalive.py              # 常駐守護模式（預設每 4.5 小時觸發一次）
    python start_keepalive.py --once       # 僅執行單次測試 Ping
    python start_keepalive.py --hours 4    # 自訂間隔為每 4 小時
=============================================================================
"""

import os
import sys
import subprocess
from pathlib import Path

# 確保在 Windows CP950 等編碼環境下輸出 Emoji 符號不崩潰
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def find_python_executable(workspace_dir: Path) -> str:
    """尋找最適合的 Python 直譯器，優先使用工作區 .venv"""
    venv_bin = workspace_dir / ".venv" / "bin" / "python"
    venv_win = workspace_dir / ".venv" / "Scripts" / "python.exe"

    if venv_bin.is_file():
        return str(venv_bin)
    elif venv_win.is_file():
        return str(venv_win)
    elif sys.executable:
        return sys.executable
    return "python3"

def main():
    script_dir = Path(__file__).resolve().parent
    workspace_dir = script_dir.parent
    logs_dir = script_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    print("══════════════════════════════════════════════════")
    print("🛡️  正在啟動 Gemini Model Quota 守護維持系統")
    print("══════════════════════════════════════════════════")

    python_cmd = find_python_executable(workspace_dir)
    target_script = script_dir / "quota_keepalive.py"

    if not target_script.exists():
        print(f"❌ 找不到目標腳本: {target_script}")
        sys.exit(1)

    cmd = [python_cmd, str(target_script)] + sys.argv[1:]

    try:
        # 直接執行並即時轉發輸入與輸出
        ret = subprocess.run(cmd)
        sys.exit(ret.returncode)
    except KeyboardInterrupt:
        print("\n👋 已手動中斷 Quota 守護維持系統。")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 啟動失敗: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
