import subprocess
import time
import sys
import os

os.chdir(r"D:\Users\Desktop\实习工作\week3\ai-data-agent - v4\backend")

# Kill existing processes
print("Killing existing Python processes...")
subprocess.run("taskkill /F /IM python.exe", shell=True, capture_output=True)
time.sleep(2)

# Start server
print("\nStarting server...")
server_process = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

# Wait and check if server started
print("Waiting 10 seconds for server to start...")
time.sleep(10)

# Test with curl
print("\nTesting endpoint with curl...")
result = subprocess.run(
    ['curl', '-X', 'POST', 'http://localhost:8000/api/v1/chat/stream',
     '-H', 'Content-Type: application/json',
     '-d', '{"message": "查询最近七天的订单数量和订单总金额", "session_id": "test_f11_final_run"}',
     '-N'],
    capture_output=True,
    text=True,
    timeout=120
)

print("\n" + "="*80)
print("SSE EVENTS:")
print("="*80)
print(result.stdout)

if result.stderr:
    print("\nSTDERR:")
    print(result.stderr)

# Check logs
print("\n" + "="*80)
print("LAST 100 LINES OF LOG:")
print("="*80)
try:
    with open("logs/app.log", "r", encoding="utf-8") as f:
        lines = f.readlines()
        for line in lines[-100:]:
            print(line.rstrip())
except Exception as e:
    print(f"Error reading log: {e}")

# Cleanup
print("\n" + "="*80)
print("Terminating server...")
server_process.terminate()
time.sleep(2)
subprocess.run("taskkill /F /IM python.exe", shell=True, capture_output=True)
print("Done!")
