"""
F-22: Chanjet IP 定位 API 端到端测试
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8002"

def test_ip_location():
    # 测试问题
    question = "查询 IP 49.67.207.11 的位置"

    print(f"\n{'='*60}")
    print(f"测试问题: {question}")
    print(f"{'='*60}\n")

    # 发送请求
    response = requests.post(
        f"{BASE_URL}/api/v1/chat",
        json={
            "session_id": "test_ip_location",
            "message": question,
            "user_id": "admin"
        },
        timeout=120
    )

    print(f"状态码: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"\n最终回答:\n{result.get('response', {}).get('text', 'No response')}")

        # 保存完整结果
        with open("backend/ip_test_result.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n完整结果已保存到: backend/ip_test_result.json")
        return True
    else:
        print(f"错误: {response.text}")
        return False

if __name__ == "__main__":
    success = test_ip_location()
    exit(0 if success else 1)
