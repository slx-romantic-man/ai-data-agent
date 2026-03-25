@echo off
echo ========================================
echo F-11 E2E Test - Server Start and Test
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] Starting backend server...
start "Backend Server" cmd /k "python -m uvicorn app.main:app --reload"

echo [2/3] Waiting for server to start (10 seconds)...
timeout /t 10 /nobreak > nul

echo [3/3] Running E2E test...
python run_e2e_test.py

echo.
echo ========================================
echo Test completed. Press any key to exit.
pause > nul
