@echo off
echo Killing existing Python processes...
taskkill /F /IM python.exe 2>nul

echo.
echo Starting server...
cd /d "D:\Users\Desktop\实习工作\week3\ai-data-agent - v4\backend"
start /B python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

echo Waiting 10 seconds for server to start...
timeout /t 10 /nobreak

echo.
echo Testing endpoint...
curl -X POST http://localhost:8000/api/v1/chat/stream -H "Content-Type: application/json" -d "{\"message\": \"查询最近七天的订单数量和订单总金额\", \"session_id\": \"test_f11_final_run\"}" -N

echo.
echo.
echo Checking logs...
echo ==================== LAST 100 LINES OF LOG ====================
powershell -Command "Get-Content logs\app.log -Tail 100"

echo.
echo Press any key to kill the server...
pause
taskkill /F /IM python.exe
