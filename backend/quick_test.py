import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import time

BASE_URL = "http://127.0.0.1:8002"

session_id = f"quick_test_{int(time.time())}"
question = "苹果股价"

print(f"发送问题: {question}")
response = requests.post(
    f"{BASE_URL}/api/v1/chat",
    json={
        "session_id": session_id,
        "message": question,
        "user_id": "admin"
    }
)

print(f"HTTP状态: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"响应键: {list(data.keys())}")
else:
    print(f"错误: {response.text}")

print("\n等待10秒...")
time.sleep(10)

history_response = requests.get(f"{BASE_URL}/api/v1/sessions/{session_id}/history")
print(f"\n历史状态: {history_response.status_code}")
if history_response.status_code == 200:
    history = history_response.json()
    messages = history.get("messages", [])
    print(f"消息数量: {len(messages)}")
    for msg in messages[-3:]:
        print(f"  - {msg.get('role')}: {msg.get('content')[:100]}...")
