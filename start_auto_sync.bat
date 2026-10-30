@echo off
cd /d "%~dp0"
title SecureVault Cloud Auto-Sync
echo ========================================================
echo   SecureVault Real-Time Cloud-to-Antigravity Auto-Sync
echo ========================================================
echo.
python auto_sync.py
pause

