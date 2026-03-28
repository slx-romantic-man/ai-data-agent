"""Simple F-12 test - check if Analyzer handles empty data"""
import requests
import json
import sys

# Fix encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

response = requests.post(
    "http://localhost:8002/api/v1/chat/stream",
    json={
        "message": "查询股票代码999999的数据",
        "session_id": "test_simple"
    },
    stream=True,
    timeout=60
)

print("Response status:", response.status_code)
print("\nSSE Events:")

answer = None
error_msg = None
for line in response.iter_lines():
    if line:
        line = line.decode('utf-8')
        if line.startswith("data: "):
            try:
                data = json.loads(line[6:])
                event_type = data.get("type", "unknown")

                if event_type == "error":
                    error_msg = data.get("data", {}).get("content", "")
                    print(f"  [ERROR] {error_msg}")
                elif event_type == "answer":
                    answer = data.get("data", {}).get("content", "")
                    print(f"  [ANSWER] {answer[:100]}...")
                else:
                    print(f"  [{event_type}]")
            except Exception as e:
                print(f"  [parse error: {e}]")

print(f"\n\nAnswer Found: {answer is not None and len(answer) > 0}")
print(f"Error Found: {error_msg is not None}")
if answer:
    print(f"\nAnswer Content:\n{answer}")
if error_msg:
    print(f"\nError Message:\n{error_msg}")
