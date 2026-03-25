import urllib.request, json, sys

data = json.dumps({"message": "查询最近七天的订单数量和订单总金额", "session_id": "test_f11_orders_ready"}).encode('utf-8')
req = urllib.request.Request(
    "http://localhost:8000/api/v1/chat/stream",
    data=data,
    headers={"Content-Type": "application/json"}
)
outfile = open("sse_out.txt", "w", encoding="utf-8")
errfile = open("sse_err.txt", "w", encoding="utf-8")
try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        outfile.write("HTTP Status: " + str(resp.status) + "\n")
        outfile.flush()
        while True:
            line = resp.readline()
            if not line:
                break
            l = line.decode("utf-8").strip()
            if l.startswith("data:"):
                outfile.write(l + "\n")
                outfile.flush()
    outfile.write("Stream ended.\n")
except Exception as e:
    errfile.write("Error: " + type(e).__name__ + " " + str(e) + "\n")
finally:
    outfile.close()
    errfile.close()
