@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PYTHON_CMD="
where py >nul 2>&1 && py -3 -c "import sys; raise SystemExit(0 if (3,10) <= sys.version_info[:2] < (3,14) else 1)" >nul 2>&1 && set "PYTHON_CMD=py -3"
if not defined PYTHON_CMD where python >nul 2>&1 && python -c "import sys; raise SystemExit(0 if (3,10) <= sys.version_info[:2] < (3,14) else 1)" >nul 2>&1 && set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
  echo [ERROR] Python 3.10-3.13 is required.
  exit /b 1
)

REM Verify the sealed source before installing any third-party package.
%PYTHON_CMD% scripts\verify_release.py
if errorlevel 1 exit /b 1
%PYTHON_CMD% scripts\security_check.py --root .
if errorlevel 1 exit /b 1

%PYTHON_CMD% -m venv .venv
if errorlevel 1 exit /b 1

.venv\Scripts\python.exe -m pip --isolated install --disable-pip-version-check --no-input --only-binary=:all: --require-hashes -r requirements.lock.txt
if errorlevel 1 exit /b 1

.venv\Scripts\python.exe bot.py verify
if errorlevel 1 exit /b 1

echo.
echo Setup complete. Next: START_WINDOWS.bat
exit /b 0
