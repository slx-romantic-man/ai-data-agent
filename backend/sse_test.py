import urllib.request, json, sys

data = json.dumps({"message": "查询最近七天的订单数量和订单总金额", "session_id": "test_f11_orders_ready"}).encode('utf-8')
req = urllib.request.Request(
    "http://localhost:8000/api/v1/chat/stream",
    data=data,
    headers={"Content-Type": "application/json"}
)
try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        print("HTTP Status:", resp.status)
        while True:
            line = resp.readline()
            if not line:
                break
            l = line.decode("utf-8").strip()
            if l.startswith("data:"):
                print(l)
                sys.stdout.flush()
    print("Stream ended.")
except Exception as e:
    print("Error:", type(e).__name__, str(e))
