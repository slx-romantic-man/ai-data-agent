#!/usr/bin/env python3
"""Test F-18: Python exec execution via chat stream"""
import requests
import json

url = "http://localhost:8002/api/v1/chat/stream"
payload = {
    "message": "上个月销售额10000，这个月12000，增长率是多少？",
    "session_id": "test_f18_exec"
}

print("Sending request...")
response = requests.post(url, json=payload, stream=True)

print(f"Status: {response.status_code}")
print("\nStream output:")
print("-" * 80)

for line in response.iter_lines():
    if line:
        decoded = line.decode('utf-8')
        if decoded.startswith('data: '):
            data = decoded[6:]
            try:
                event = json.loads(data)
                print(json.dumps(event, ensure_ascii=False, indent=2))
            except:
                print(data)
