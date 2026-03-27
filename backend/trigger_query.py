"""
Simple test to trigger a query and generate logs
"""
import requests
import json

BASE_URL = "http://localhost:8002"

# Step 1: Login
print("1. Logging in...")
login_response = requests.post(
    f"{BASE_URL}/api/v1/auth/login",
    data={
        "username": "user1",
        "password": "user123"
    }
)

if login_response.status_code != 200:
    print(f"Login failed: {login_response.status_code}")
    print(login_response.text)
    exit(1)

token = login_response.json()["access_token"]
print(f"Login successful, token: {token[:20]}...")

# Step 2: Send query
print("\n2. Sending query...")
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

payload = {
    "message": "查询苹果美股最近7个交易日股价",
    "session_id": "test_f03_trigger"
}

response = requests.post(
    f"{BASE_URL}/api/v1/chat/stream",
    headers=headers,
    json=payload,
    stream=True,
    timeout=60
)

print(f"Response status: {response.status_code}")

if response.status_code == 200:
    print("Query sent successfully, collecting events...")
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                try:
                    data = json.loads(line_str[6:])
                    event_type = data.get('type')
                    print(f"  Event: {event_type}")
                    if event_type == 'done':
                        break
                except:
                    pass
    print("\n3. Query completed. Check logs with: python test_f03_logs.py")
else:
    print(f"Query failed: {response.text}")
