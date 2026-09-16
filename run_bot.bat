@echo off
chcp 65001 > nul
cd /d "%~dp0"
title METH WAVE Shop Bot - Autorestart Daemon
echo ======================================================
echo    🤖 Запуск Telegram-бота METH WAVE с авто-рестартом
echo ======================================================

:loop
echo [%date% %time%] Запуск процесса бота...
"%~dp0venv\Scripts\python.exe" "%~dp0bot.py"
echo [%date% %time%] Бот остановлен или произошел сбой. Перезапуск через 3 секунды...
ping 127.0.0.1 -n 4 > nul
goto loop
