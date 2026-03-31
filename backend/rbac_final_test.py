"""
F-23: RBAC权限隔离验证 - 使用现有用户测试
"""
import asyncio
import requests
import sys
import io
from app.access.database.connection import get_db
from sqlalchemy import text

# 设置UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://127.0.0.1:8003"

async def setup_permissions():
    """为现有用户分配差异化权限"""
    db = await get_db()
    async with db.get_session() as session:
        # 获取三个API的ID
        result = await session.execute(text(
            "SELECT id, config_id FROM api_configs "
            "WHERE config_id IN ('alpha_vantage_stock', 'weather_api', 'ip_location_api')"
        ))
        apis = {row[1]: row[0] for row in result.fetchall()}

        if len(apis) != 3:
            print(f"错误: 只找到 {len(apis)} 个API")
            return False

        stock_id = apis['alpha_vantage_stock']
        weather_id = apis['weather_api']
        ip_id = apis['ip_location_api']

        # 清理 user_001 和 user_002 的旧权限
        await session.execute(text(
            "DELETE FROM user_api_permissions WHERE user_id IN ('user_001', 'user_002')"
        ))
        await session.commit()

        # user_001: 只有股票API权限
        await session.execute(text(
            f"INSERT INTO user_api_permissions (user_id, api_config_id, source, status) "
            f"VALUES ('user_001', {stock_id}, 'admin', 'active')"
        ))

        # user_002: 只有天气API权限
        await session.execute(text(
            f"INSERT INTO user_api_permissions (user_id, api_config_id, source, status) "
            f"VALUES ('user_002', {weather_id}, 'admin', 'active')"
        ))

        await session.commit()

        print("权限配置完成:")
        print(f"  user_001: 股票API (ID: {stock_id})")
        print(f"  user_002: 天气API (ID: {weather_id})")
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
        print(f"  HTTP错误: {response.status_code}")
        return False

    data = response.json()
    final_answer = data.get("response", {}).get("text", "")

    # 打印前200字符用于调试
    print(f"  回答预览: {final_answer[:200]}")

    if expected_success:
        if "权限" in final_answer or "无权" in final_answer or "拒绝" in final_answer:
            print(f"  失败: 应该成功但被拒绝")
            return False
        print(f"  成功: 获得有效回答")
        return True
    else:
        if "权限" in final_answer or "无权" in final_answer or "拒绝" in final_answer:
            print(f"  成功: 正确拒绝")
            return True
        print(f"  失败: 应该拒绝但返回了结果")
        return False

async def main():
    print("=" * 60)
    print("F-23: RBAC权限隔离验证")
    print("=" * 60)

    print("\n[步骤1] 配置差异化权限...")
    if not await setup_permissions():
        print("权限配置失败")
        return False

    print("\n[步骤2] user_001 查询股票 (应该成功)...")
    test1 = test_query("user_001", "查询苹果公司股票", True)

    print("\n[步骤3] user_001 查询天气 (应该拒绝)...")
    test2 = test_query("user_001", "查询上海天气", False)

    print("\n[步骤4] user_002 查询天气 (应该成功)...")
    test3 = test_query("user_002", "查询北京天气", True)

    print("\n[步骤5] user_002 查询股票 (应该拒绝)...")
    test4 = test_query("user_002", "查询特斯拉股票", False)

    print("\n" + "=" * 60)
    print("测试结果:")
    print(f"  user_001 查询股票: {'通过' if test1 else '失败'}")
    print(f"  user_001 查询天气: {'通过' if test2 else '失败'}")
    print(f"  user_002 查询天气: {'通过' if test3 else '失败'}")
    print(f"  user_002 查询股票: {'通过' if test4 else '失败'}")

    all_pass = all([test1, test2, test3, test4])
    print(f"\n最终结果: {'全部通过' if all_pass else '存在失败'}")
    print("=" * 60)

    return all_pass

if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)
