@echo off
cd /d "%~dp0"
title Telegram Bot

if not exist "%~dp0venv\Scripts\python.exe" (
    echo ERROR: Python virtual environment was not found.
    echo Create it with: python -m venv venv
    echo Install packages with: venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

:loop
echo Starting bot...
"%~dp0venv\Scripts\python.exe" "%~dp0bot.py"
echo Bot stopped. Restarting in 3 seconds...
timeout /t 3 /nobreak > nul
goto loop
