@echo off
setlocal
cd /d "%~dp0"
echo ResolveIQ - local incident workspace
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher was not found. Install Python 3.11 or newer from python.org, then retry.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo.
echo Open http://127.0.0.1:8000 in your browser after the server starts.
echo Press Ctrl+C here to stop the server.
".venv\Scripts\python.exe" run.py
if errorlevel 1 goto failed
exit /b 0
:failed
echo Setup or launch failed. Read the error above and see START_HERE.md.
pause
exit /b 1
