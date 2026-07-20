@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Setup is not complete. Run SETUP_WINDOWS.bat first.
  pause
  exit /b 1
)
.venv\Scripts\python.exe bot.py menu
set "CODE=%ERRORLEVEL%"
if not "%CODE%"=="0" pause
exit /b %CODE%
