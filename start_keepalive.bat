@echo off
chcp 65001 >nul
echo ══════════════════════════════════════════════════
echo 🛡️ 正在啟動 Gemini Model Quota 守護維持系統 (Windows)
echo ══════════════════════════════════════════════════

set SCRIPT_DIR=%~dp0
set VENV_PYTHON=%SCRIPT_DIR%..\.venv\Scripts\python.exe

if exist "%VENV_PYTHON%" (
    "%VENV_PYTHON%" "%SCRIPT_DIR%quota_keepalive.py" %*
) else (
    python "%SCRIPT_DIR%quota_keepalive.py" %*
)

pause
