#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
start_monitor.py
=============================================================================
跨平台 Gemini API 使用狀況監控儀表板啟動腳本 (macOS / Windows / Linux 通用)

功能說明：
1. 跨平台自動偵測工作區虛擬環境 (.venv)，優先使用專案虛擬環境之 Python 直譯器。
2. 自動於背景延遲開啟瀏覽器 (預設 http://localhost:8502)。
3. 啟動 Streamlit 視覺化監控前端 (app_monitor.py)，支援自訂參數轉發。
4. 處理終端機中斷訊號與編碼容錯。

使用方式：
    python start_monitor.py                         # 預設啟動於 Port 8502
    python start_monitor.py --server.port 8503      # 自訂 Port
=============================================================================
"""

import os
import sys
import time
import threading
import webbrowser
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

def open_browser_delayed(url: str, delay: float = 1.5):
    """延遲一段時間後自動於預設瀏覽器開啟 URL"""
    def _open():
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:
            pass
    t = threading.Thread(target=_open, daemon=True)
    t.start()

def main():
    script_dir = Path(__file__).resolve().parent
    workspace_dir = script_dir.parent

    print("══════════════════════════════════════════════════")
    print("🤖 正在啟動 Gemini API 使用狀況監控儀表板 (Streamlit)")
    print("══════════════════════════════════════════════════")

    python_cmd = find_python_executable(workspace_dir)
    app_script = script_dir / "app_monitor.py"

    if not app_script.exists():
        print(f"❌ 找不到目標前端腳本: {app_script}")
        sys.exit(1)

    port = "8502"
    extra_args = sys.argv[1:]

    # 解析自訂 Port
    for i, a in enumerate(extra_args):
        if a in ("--server.port", "--port") and i + 1 < len(extra_args):
            port = extra_args[i + 1]
            break
        elif a.startswith("--server.port="):
            port = a.split("=", 1)[1]
            break
        elif a.startswith("--port="):
            port = a.split("=", 1)[1]
            break

    # 組裝 Streamlit 指令
    cmd_args = ["-m", "streamlit", "run", str(app_script)]

    if not any("--server.port" in a for a in extra_args):
        cmd_args.extend(["--server.port", port])
    if not any("--server.address" in a for a in extra_args):
        cmd_args.extend(["--server.address", "localhost"])
    if not any("--server.headless" in a for a in extra_args):
        cmd_args.extend(["--server.headless", "false"])

    cmd_args.extend(extra_args)
    cmd = [python_cmd] + cmd_args

    # 自動於背景延遲開啟瀏覽器
    open_browser_delayed(f"http://localhost:{port}")

    try:
        ret = subprocess.run(cmd)
        sys.exit(ret.returncode)
    except KeyboardInterrupt:
        print("\n👋 已手動關閉 Streamlit 監控儀表板。")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 啟動失敗: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
