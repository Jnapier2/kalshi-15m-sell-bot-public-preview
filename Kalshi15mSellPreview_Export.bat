@echo off
setlocal
rem Copyright © 2026 Gateway Information Group LLC. All rights reserved.
pushd "%~dp0" || exit /b 2
py -3 -I -S -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 2)" >nul 2>&1
if not errorlevel 1 goto use_py
python -I -S -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 2)" >nul 2>&1
if not errorlevel 1 goto use_python
echo Python 3.11 or newer is required. No installation was attempted.
popd
exit /b 2
:use_py
py -3 -I -S -B "%~dp0public_support.py" --export
goto done
:use_python
python -I -S -B "%~dp0public_support.py" --export
:done
set "RESULT=%ERRORLEVEL%"
popd
exit /b %RESULT%
