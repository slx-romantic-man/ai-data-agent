@echo off
echo ========================================
echo F-11 Final Test - Restart and Test
echo ========================================
echo.
echo This will:
echo 1. Kill existing Python server
echo 2. Start fresh server with ALL fixes
echo 3. Wait 15 seconds for initialization
echo 4. Run orders query test
echo.
pause

cd /d "%~dp0"

echo.
echo [1/4] Killing existing Python processes...
taskkill /F /IM python.exe 2>nul
timeout /t 3 /nobreak > nul

echo [2/4] Starting backend server...
start "Backend Server" cmd /k "python -m uvicorn app.main:app --reload"

echo [3/4] Waiting for server to initialize (15 seconds)...
timeout /t 15 /nobreak > nul

echo [4/4] Running orders query test...
echo.
python test_orders_query.py

echo.
echo ========================================
echo Test completed. Check results above.
echo ========================================
pause
