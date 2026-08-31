@echo off
chcp 65001 >nul
echo ══════════════════════════════════════════════════
echo 🤖 正在啟動 Gemini API 使用狀況監控儀表板 (Streamlit)
echo ══════════════════════════════════════════════════

set SCRIPT_DIR=%~dp0
set VENV_PYTHON=%SCRIPT_DIR%..\.venv\Scripts\python.exe

if exist "%VENV_PYTHON%" (
    "%VENV_PYTHON%" -m streamlit run "%SCRIPT_DIR%app_monitor.py" --server.port 8502 --server.address localhost
) else (
    python -m streamlit run "%SCRIPT_DIR%app_monitor.py" --server.port 8502 --server.address localhost
)

pause
