@echo off
echo ========================================
echo F-11 E2E Test - Restart Server and Test
echo ========================================
echo.

cd /d "%~dp0"

echo [1/4] Stopping existing server...
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak > nul

echo [2/4] Starting backend server...
start "Backend Server" cmd /k "python -m uvicorn app.main:app --reload"

echo [3/4] Waiting for server to start (15 seconds)...
timeout /t 15 /nobreak > nul

echo [4/4] Running E2E test...
python run_e2e_test.py

echo.
echo ========================================
echo Test completed. Check output above.
echo Press any key to exit.
pause > nul
