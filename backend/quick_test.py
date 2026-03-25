import requests
import json

url = "http://localhost:8000/api/v1/chat"
payload = {
    "conversation_id": "test-f11-sync",
    "message": "查询最近七天的订单数量和订单总金额",
    "user_id": "test_user"
}

print("Testing orders query...")
try:
    r = requests.post(url, json=payload, timeout=120)
    result = r.json()
    text = result.get("response", {}).get("text", "")
    print(f"\nStatus: {r.status_code}")
    print(f"Response text: {text[:300]}")

    if "未能获取" in text:
        print("\n❌ FAILED: Still no data")
    elif "订单" in text:
        print("\n✓ SUCCESS: Got orders data")
    else:
        print(f"\n⚠ Check response")
except Exception as e:
    print(f"Error: {e}")
