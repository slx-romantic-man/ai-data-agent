"""
F-23: RBAC权限隔离验证 - 完整端到端测试
"""
import asyncio
import requests
import json
from app.access.database.connection import get_db
from sqlalchemy import text

BASE_URL = "http://127.0.0.1:8003"

async def setup_test_users():
    """创建测试用户并分配权限"""
    db = await get_db()
    async with db.get_session() as session:
        # 1. 清理旧测试用户 (使用单独的DELETE避免子查询问题)
        await session.execute(text("DELETE FROM user_api_permissions WHERE user_id = 'user_a'"))
        await session.execute(text("DELETE FROM user_api_permissions WHERE user_id = 'user_b'"))
        await session.execute(text("DELETE FROM user_quotas WHERE user_id = 'user_a'"))
        await session.execute(text("DELETE FROM user_quotas WHERE user_id = 'user_b'"))
        await session.execute(text("DELETE FROM user_accounts WHERE user_id = 'user_a'"))
        await session.execute(text("DELETE FROM user_accounts WHERE user_id = 'user_b'"))
        await session.commit()

        # 2. 创建 user_a 和 user_b
        await session.execute(text(
            "INSERT INTO user_accounts (user_id, username, password, role, department) "
            "VALUES ('user_a', 'User A', 'test123', 'employee', 'test')"
        ))
        await session.execute(text(
            "INSERT INTO user_accounts (user_id, username, password, role, department) "
            "VALUES ('user_b', 'User B', 'test123', 'employee', 'test')"
        ))

        # 3. 创建配额
        await session.execute(text(
            "INSERT INTO user_quotas (user_id, daily_limit, current_balance) "
            "VALUES ('user_a', 1000, 1000), ('user_b', 1000, 1000)"
        ))
        await session.commit()

        # 4. 获取三个API的ID
        result = await session.execute(text(
            "SELECT id, config_id, name FROM api_configs "
            "WHERE config_id IN ('alpha_vantage_stock', 'weather_api', 'ip_location_api')"
        ))
        apis = {row[1]: row[0] for row in result.fetchall()}

        if len(apis) != 3:
            print(f"错误: 只找到 {len(apis)} 个API: {list(apis.keys())}")
            return False

        # 5. 分配权限: user_a -> 股票, user_b -> 天气
        await session.execute(text(
            "INSERT INTO user_api_permissions (user_id, api_config_id, can_read, can_write) "
            f"VALUES ('user_a', {apis['alpha_vantage_stock']}, 1, 0)"
        ))
        await session.execute(text(
            "INSERT INTO user_api_permissions (user_id, api_config_id, can_read, can_write) "
            f"VALUES ('user_b', {apis['weather_api']}, 1, 0)"
        ))
        await session.commit()

        print("测试用户创建完成:")
        print(f"  user_a: 股票API权限 (API ID: {apis['alpha_vantage_stock']})")
        print(f"  user_b: 天气API权限 (API ID: {apis['weather_api']})")
        return True

def test_query(user_id, question, expected_success):
    """测试查询"""
    print(f"\n[{user_id}] 查询: {question}")

    response = requests.post(
        f"{BASE_URL}/api/v1/chat",
        json={
            "session_id": f"test_rbac_{user_id}",
            "message": question,
            "user_id": user_id
        },
        timeout=120
    )

    if response.status_code != 200:
        print(f"  状态码: {response.status_code}")
        return False

    data = response.json()
    final_answer = data.get("response", {}).get("text", "")

    if expected_success:
        # 应该成功
        if "权限" in final_answer or "无权" in final_answer or "拒绝" in final_answer:
            print(f"  失败: 应该成功但被拒绝")
            print(f"  回答: {final_answer[:200]}")
            return False
        print(f"  成功: 获得有效回答")
        return True
    else:
        # 应该被拒绝
        if "权限" in final_answer or "无权" in final_answer or "拒绝" in final_answer:
            print(f"  成功: 正确拒绝")
            return True
        print(f"  失败: 应该拒绝但返回了结果")
        print(f"  回答: {final_answer[:200]}")
        return False

async def main():
    print("=" * 60)
    print("F-23: RBAC权限隔离验证")
    print("=" * 60)

    # 步骤1: 创建测试用户
    print("\n[步骤1] 创建测试用户...")
    if not await setup_test_users():
        print("环境准备失败")
        return

    # 步骤2-3: user_a 查询股票 (应该成功)
    print("\n[步骤2] user_a 查询股票 (应该成功)...")
    test1 = test_query("user_a", "查询苹果公司股票", True)

    # 步骤4: user_a 查询天气 (应该拒绝)
    print("\n[步骤3] user_a 查询天气 (应该拒绝)...")
    test2 = test_query("user_a", "查询上海天气", False)

    # 步骤5: user_b 查询天气 (应该成功)
    print("\n[步骤4] user_b 查询天气 (应该成功)...")
    test3 = test_query("user_b", "查询北京天气", True)

    # 步骤6: user_b 查询股票 (应该拒绝)
    print("\n[步骤5] user_b 查询股票 (应该拒绝)...")
    test4 = test_query("user_b", "查询特斯拉股票", False)

    # 总结
    print("\n" + "=" * 60)
    print("测试结果:")
    print(f"  user_a 查询股票: {'通过' if test1 else '失败'}")
    print(f"  user_a 查询天气: {'通过' if test2 else '失败'}")
    print(f"  user_b 查询天气: {'通过' if test3 else '失败'}")
    print(f"  user_b 查询股票: {'通过' if test4 else '失败'}")

    all_pass = all([test1, test2, test3, test4])
    print(f"\n最终结果: {'全部通过' if all_pass else '存在失败'}")
    print("=" * 60)

    return all_pass

if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)
