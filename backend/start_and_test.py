import subprocess
import time
import requests
import json
import sys

# Start the server
print("Starting server...")
process = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
    cwd=r"D:\Users\Desktop\实习工作\week3\ai-data-agent - v4\backend",
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# Wait for server to start
print("Waiting 10 seconds for server to start...")
time.sleep(10)

# Test the endpoint
print("\nTesting endpoint...")
url = "http://localhost:8000/api/v1/chat/stream"
payload = {
    "message": "查询最近七天的订单数量和订单总金额",
    "session_id": "test_f11_final_run"
}

try:
    response = requests.post(url, json=payload, stream=True, timeout=120)
    print(f"Response status: {response.status_code}\n")
    print("SSE Events:")
    print("-" * 80)

    for line in response.iter_lines():
        if line:
            decoded = line.decode('utf-8')
            print(decoded)

except Exception as e:
    print(f"Error: {e}")
finally:
    # Kill the server
    process.terminate()
    print("\n" + "-" * 80)
    print("Server terminated")
