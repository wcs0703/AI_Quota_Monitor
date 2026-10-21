@echo off
chcp 65001 >nul

set SCRIPT_DIR=%~dp0
set VENV_PYTHON=%SCRIPT_DIR%..\.venv\Scripts\python.exe

if exist "%VENV_PYTHON%" (
    "%VENV_PYTHON%" "%SCRIPT_DIR%start_monitor.py" %*
) else (
    python "%SCRIPT_DIR%start_monitor.py" %*
)

pause
