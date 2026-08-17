@echo off
chcp 65001 >nul
echo ══════════════════════════════════════════════════
echo 🛡️  正在啟動 Gemini Model Quota 守護維持系統 (Windows)
echo ══════════════════════════════════════════════════

python quota_keepalive.py %*
pause
