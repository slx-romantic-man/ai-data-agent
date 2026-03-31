"""
F-23: RBAC 权限隔离验证 - 用户和权限设置
通过 HTTP API 创建测试用户并分配权限
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8003"

def create_user(username, email, password, full_name):
    """创建用户"""
    response = requests.post(
        f"{BASE_URL}/api/v1/users/register",
        json={
            "username": username,
            "email": email,
            "password": password,
            "full_name": full_name
        }
    )
    return response

def login(username, password):
    """用户登录获取 token"""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        data={
            "username": username,
            "password": password
        }
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    return None

def get_api_list(token):
    """获取 API 列表"""
    response = requests.get(
        f"{BASE_URL}/api/v1/apis",
        headers={"Authorization": f"Bearer {token}"}
    )
    return response.json() if response.status_code == 200 else []

def assign_permission(admin_token, user_id, api_id):
    """管理员为用户分配 API 权限"""
    response = requests.post(
        f"{BASE_URL}/api/v1/permissions",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "user_id": user_id,
            "api_config_id": api_id,
            "can_read": True,
            "can_write": False
        }
    )
    return response

def main():
    print("=" * 60)
    print("F-23: RBAC 权限隔离验证 - 环境准备")
    print("=" * 60)

    # 1. 创建测试用户
    print("\n[步骤 1] 创建测试用户...")

    user_a_resp = create_user("user_a", "user_a@test.com", "test123", "Test User A")
    print(f"user_a 创建: {user_a_resp.status_code}")

    user_b_resp = create_user("user_b", "user_b@test.com", "test123", "Test User B")
    print(f"user_b 创建: {user_b_resp.status_code}")

    # 2. 管理员登录
    print("\n[步骤 2] 管理员登录...")
    admin_token = login("admin", "admin123")
    if not admin_token:
        print("❌ 管理员登录失败")
        return
    print("✅ 管理员登录成功")

    # 3. 获取 API 列表
    print("\n[步骤 3] 获取已注册的 API...")
    apis = get_api_list(admin_token)
    print(f"找到 {len(apis)} 个 API")

    # 查找三个外部 API
    stock_api = next((api for api in apis if "stock" in api.get("config_id", "").lower()), None)
    weather_api = next((api for api in apis if "weather" in api.get("config_id", "").lower()), None)
    ip_api = next((api for api in apis if "ip" in api.get("config_id", "").lower()), None)

    if not all([stock_api, weather_api, ip_api]):
        print("❌ 未找到全部三个外部 API")
        print(f"股票 API: {stock_api}")
        print(f"天气 API: {weather_api}")
        print(f"IP API: {ip_api}")
        return

    print(f"✅ 股票 API: {stock_api['name']}")
    print(f"✅ 天气 API: {weather_api['name']}")
    print(f"✅ IP API: {ip_api['name']}")

    print("\n✅ 环境准备完成")
    print("\n下一步: 运行 rbac_test.py 进行权限隔离测试")

if __name__ == "__main__":
    main()
