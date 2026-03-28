import requests
import json
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("Testing F-12: Analyzer empty data handling...")
print("="*60)

response = requests.post(
    "http://localhost:8002/api/v1/chat/stream",
    json={"message": "查询不存在的数据", "session_id": "f12_verify"},
    stream=True,
    timeout=45
)

answer_found = False
for line in response.iter_lines():
    if line:
        line = line.decode('utf-8')
        if line.startswith("data: "):
            try:
                data = json.loads(line[6:])
                if data.get("type") == "answer":
                    content = data.get("data", {}).get("content", "")
                    if content:
                        answer_found = True
                        print(f"\n✓ Answer received ({len(content)} chars)")
                        print(f"\nContent preview:\n{content[:300]}")
                        break
            except:
                pass

if answer_found:
    print("\n✓ F-12 PASS: Analyzer returns non-empty answer")
else:
    print("\n✗ F-12 FAIL: No answer received")
