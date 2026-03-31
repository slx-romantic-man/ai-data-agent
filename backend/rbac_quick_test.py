"""Quick RBAC test - single request"""
import requests
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://127.0.0.1:8003"

print("Testing user_001 with stock query...")
response = requests.post(
    f"{BASE_URL}/api/v1/chat",
    json={
        "session_id": "test_quick",
        "message": "查询苹果公司股票",
        "user_id": "user_001"
    },
    timeout=30
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    answer = data.get("response", {}).get("text", "")
    print(f"Answer preview: {answer[:200]}")

    if "权限" in answer or "无权" in answer:
        print("FAIL: Permission denied")
    else:
        print("PASS: Got valid response")
else:
    print(f"ERROR: {response.text}")
