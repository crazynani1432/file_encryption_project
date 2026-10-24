@echo off
title Secure Multi-Tier File Vault
echo =========================================================
echo    Secure Multi-Tier Hybrid Cryptographic File Vault
echo =========================================================
echo.

if not exist .env (
    echo [!] Warning: .env file not detected.
    echo [*] Creating .env from .env.example...
    copy .env.example .env
    echo [*] Please configure your .env file with appropriate keys.
    echo.
)

echo [*] Launching FastAPI Web Application...
python run.py
pause
