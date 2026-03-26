@echo off
title ShortsForge Scheduler
cd /d "%~dp0"
if exist "venv\Scripts\activate.bat" call venv\Scripts\activate.bat
python scheduler.py start
pause
