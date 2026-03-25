import urllib.request
import json

url = "http://localhost:8000/api/v1/chat/stream"
data = json.dumps({"message": "查询最近七天的订单数量和订单总金额", "session_id": "test_f11_final"}).encode()

req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

print("=== SSE EVENTS ===")
try:
    with urllib.request.urlopen(req, timeout=120) as response:
        for line in response:
            line = line.decode('utf-8').strip()
            if line:
                print(line)
except Exception as e:
    print(f"Error: {e}")
