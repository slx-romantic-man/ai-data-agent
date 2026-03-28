"""Test F-12: Analyzer handles empty data scenario"""
import requests
import json
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Test with a specific stock query that should return no data
response = requests.post(
    "http://localhost:8002/api/v1/chat/stream",
    json={
        "message": "查询股票代码600000在2099年1月1日的收盘价",
        "session_id": "test_empty_data"
    },
    stream=True,
    timeout=60
)

print("Response status:", response.status_code)
print("\nSSE Events:")

answer = None
for line in response.iter_lines():
    if line:
        line = line.decode('utf-8')
        if line.startswith("data: "):
            try:
                data = json.loads(line[6:])
                event_type = data.get("type", "unknown")

                if event_type == "answer":
                    answer = data.get("data", {}).get("content", "")
                    print(f"  [ANSWER] {answer[:150]}...")
                elif event_type == "thought":
                    content = data.get("data", {}).get("content", "")
                    print(f"  [THOUGHT] {content}")
                else:
                    print(f"  [{event_type}]")
            except Exception as e:
                print(f"  [parse error: {e}]")

print(f"\n{'='*60}")
print("Result:")
print(f"{'='*60}")
if answer:
    print(f"Answer: {answer}")
    print(f"\nLength: {len(answer)}")

    # Check if answer contains proper error handling
    has_proper_message = any(keyword in answer for keyword in [
        "未能获取", "未查询到", "没有", "无法", "抱歉", "不足"
    ])
    print(f"Has proper error message: {has_proper_message}")
else:
    print("ERROR: No answer received!")
