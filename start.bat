@echo off
setlocal EnableExtensions
echo [START] Multi-Strategy System Analysis

REM Resolve Python interpreter
set "PY=python"
where python3 >nul 2>&1 && set "PY=python3"
if exist "venv\Scripts\python.exe" set "PY=venv\Scripts\python.exe"

echo [INFO] Using interpreter: %PY%

REM Dependency check
echo [INFO] Checking dependencies...
"%PY%" -m pip show flask >nul 2>&1
if errorlevel 1 (
  echo [INFO] Installing requirements...
  "%PY%" -m pip install -r requirements.txt
)

REM Start application
echo [INFO] Starting web app...
echo [INFO] Visit: http://127.0.0.1:8383
echo [INFO] Press Ctrl+C to stop

"%PY%" app.py

endlocal