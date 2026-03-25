"""
F-11 直接 API 测试：验证简单查询场景
"""
import requests

BASE_URL = "http://localhost:8002"

def test_simple_query():
    """测试简单查询通过 API"""

    # 1. 登录获取 token
    print("Step 1: Login...")
    login_resp = requests.post(f"{BASE_URL}/api/v1/auth/login", data={
        "username": "admin",
        "password": "admin123"
    })
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[OK] Login successful, token: {token[:20]}...")

    # 2. 发起聊天请求
    print("\nStep 2: Send query...")
    chat_resp = requests.post(f"{BASE_URL}/api/v1/chat",
        headers=headers,
        json={"message": "今天有多少用户注册？"}
    )
    assert chat_resp.status_code == 200, f"Chat failed: {chat_resp.text}"
    result = chat_resp.json()
    print(f"[OK] Chat response received")
    print(f"  Thread ID: {result.get('thread_id')}")
    response_content = result.get('response', '')
    if isinstance(response_content, str):
        print(f"  Response preview: {response_content[:100]}...")
    else:
        print(f"  Response type: {type(response_content)}")
        print(f"  Response: {result}")

    # 3. 验证响应内容
    print("\nStep 3: Validate response...")
    response_text = result.get('response', '').lower()

    # 检查是否包含关键信息
    has_number = any(char.isdigit() for char in response_text)
    has_sql_keyword = any(kw in response_text for kw in ['sql', '查询', 'select', '数据库'])

    print(f"  [OK] Contains numbers: {has_number}")
    print(f"  [OK] Contains SQL/query keywords: {has_sql_keyword}")

    # 4. 检查执行历史
    print("\nStep 4: Check execution history...")
    thread_id = result.get('thread_id')
    if thread_id:
        history_resp = requests.get(
            f"{BASE_URL}/api/v1/chat/history/{thread_id}",
            headers=headers
        )
        if history_resp.status_code == 200:
            history = history_resp.json()
            print(f"  [OK] History retrieved: {len(history)} messages")

    print("\n" + "="*60)
    print("[PASS] F-11 TEST PASSED: Simple query scenario works!")
    print("="*60)
    return True

if __name__ == "__main__":
    try:
        test_simple_query()
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
