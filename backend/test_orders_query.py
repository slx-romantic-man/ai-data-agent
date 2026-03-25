"""
Quick test for orders query after server restart
"""
import requests
import json

url = "http://localhost:8000/api/v1/chat"
payload = {
    "conversation_id": "test-f11-orders",
    "message": "查询最近七天的订单数量和订单总金额",
    "user_id": "test_user"
}

print("Testing: 查询最近七天的订单数量和订单总金额")
print("=" * 60)

try:
    response = requests.post(url, json=payload, timeout=120)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print("\nResponse:")
        print(json.dumps(result, ensure_ascii=False, indent=2))

        # Check if we got actual data
        response_text = result.get("response", {}).get("text", "")
        if "未能获取到有效数据" in response_text:
            print("\n❌ FAILED: Still returning '未能获取到有效数据'")
        elif "订单" in response_text or "order" in response_text.lower():
            print("\n✓ SUCCESS: Got orders data analysis")
        else:
            print("\n⚠ UNKNOWN: Check response text above")
    else:
        print(f"Error: {response.text}")

except Exception as e:
    print(f"Exception: {e}")
