import requests
import json
import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8002/api/v1"

def test_approval_flow():
    print("=== 测试审批流程 ===\n")

    # 1. 普通用户登录
    print("1. 普通用户登录...")
    login_data = {"username": "user1", "password": "user123"}
    resp = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    if resp.status_code != 200:
        print(f"❌ 登录失败: {resp.text}")
        return

    user_token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {user_token}"}
    print(f"✓ 普通用户登录成功\n")

    # 2. 发送查询触发审批
    print("2. 发送查询（应触发审批）...")
    session_id = f"test-{int(time.time())}"

    resp = requests.post(
        f"{BASE_URL}/chat/stream",
        json={"message": "查询今天的用户总数", "session_id": session_id},
        headers=headers,
        stream=True
    )

    approval_triggered = False
    for line in resp.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                data = json.loads(line_str[6:])
                print(f"  事件: {data.get('type')}")

                if data.get('type') == 'error':
                    print(f"  错误: {data.get('data', {}).get('message', 'Unknown')}")

                if data.get('type') == 'approval_required':
                    approval_triggered = True
                    print("✓ 审批卡片触发！")
                    print(f"  Thread ID: {data['data']['thread_id']}")
                    print(f"  执行计划: {data['data']['plan']}\n")
                    break

    if not approval_triggered:
        print("❌ 普通用户未触发审批\n")
        return

    # 3. 测试审批接口
    print("3. 测试批准执行...")
    resp = requests.post(
        f"{BASE_URL}/approval/{session_id}/approve",
        headers=headers
    )
    print(f"  批准响应: {resp.json()}\n")

    # 4. 管理员登录测试
    print("4. 管理员登录...")
    admin_data = {"username": "admin", "password": "admin123"}
    resp = requests.post(f"{BASE_URL}/auth/login", data=admin_data)
    admin_token = resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print(f"✓ 管理员登录成功\n")

    # 5. 管理员查询（不应触发审批）
    print("5. 管理员查询（不应触发审批）...")
    admin_session = f"admin-test-{int(time.time())}"

    resp = requests.post(
        f"{BASE_URL}/chat/stream",
        json={"message": "查询今天的用户总数", "session_id": admin_session},
        headers=admin_headers,
        stream=True
    )

    admin_approval = False
    for line in resp.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                data = json.loads(line_str[6:])
                if data.get('type') == 'approval_required':
                    admin_approval = True
                    break
                if data.get('type') == 'done':
                    break

    if admin_approval:
        print("❌ 管理员不应触发审批")
    else:
        print("✓ 管理员直接执行，无需审批\n")

    print("=== 测试完成 ===")

if __name__ == "__main__":
    test_approval_flow()
