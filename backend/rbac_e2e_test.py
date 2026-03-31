"""
F-23: RBAC权限隔离端到端测试 - 简化版
只测试关键场景，减少超时风险
"""
import asyncio
import requests
import sys
import io
from app.access.database.connection import get_db
from sqlalchemy import text

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://127.0.0.1:8003"

async def setup_permissions():
    """配置测试权限"""
    from app.access.database.connection import DatabaseConnection
    db = DatabaseConnection()
    async with db.get_session() as session:
        # 获取API IDs
        result = await session.execute(
            text("SELECT id, config_id FROM api_configs WHERE config_id IN ('alpha_vantage_stock', 'weather_api')")
        )
        api_map = {row[1]: row[0] for row in result}
        stock_id = api_map.get('alpha_vantage_stock')
        weather_id = api_map.get('weather_api')

        # 清除旧权限
        await session.execute(
            text("DELETE FROM user_api_permissions WHERE user_id IN ('user_001', 'user_002')")
        )
        await session.commit()

        # 设置新权限
        await session.execute(
            text("INSERT INTO user_api_permissions (user_id, api_config_id, source, status) VALUES ('user_001', :stock_id, 'admin', 'active')"),
            {"stock_id": stock_id}
        )
        await session.execute(
            text("INSERT INTO user_api_permissions (user_id, api_config_id, source, status) VALUES ('user_002', :weather_id, 'admin', 'active')"),
            {"weather_id": weather_id}
        )
        await session.commit()

        print(f"权限配置: user_001→股票API({stock_id}), user_002→天气API({weather_id})")
        return stock_id, weather_id

def test_query(user_id, question, expected_success, timeout=60):
    """测试单个查询"""
    print(f"\n[{user_id}] {question}")

    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/chat",
            json={
                "session_id": f"test_{user_id}",
                "message": question,
                "user_id": user_id
            },
            timeout=timeout
        )

        if response.status_code != 200:
            print(f"  ✗ HTTP错误: {response.status_code}")
            return False

        data = response.json()
        answer = data.get("response", {}).get("text", "")

        # 检查权限拒绝关键词
        is_denied = any(kw in answer for kw in ["权限", "无权", "拒绝", "无法执行"])

        if expected_success:
            if is_denied:
                print(f"  ✗ 应该成功但被拒绝")
                return False
            print(f"  ✓ 成功获得回答")
            return True
        else:
            if is_denied:
                print(f"  ✓ 正确拒绝")
                return True
            print(f"  ✗ 应该拒绝但返回了结果")
            return False

    except requests.exceptions.Timeout:
        print(f"  ✗ 超时")
        return False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False

async def main():
    print("=" * 60)
    print("F-23: RBAC权限隔离端到端测试")
    print("=" * 60)

    # 配置权限
    print("\n[步骤1] 配置权限...")
    await setup_permissions()

    # 测试2个关键场景
    print("\n[步骤2] 执行测试...")

    results = {}

    # 测试1: user_001查询股票（应该成功）
    results['user_001_stock'] = test_query("user_001", "查询苹果公司最新股价", True, timeout=90)

    # 测试2: user_002查询股票（应该拒绝）
    results['user_002_stock'] = test_query("user_002", "查询特斯拉股票", False, timeout=90)

    # 结果
    print("\n" + "=" * 60)
    print("测试结果:")
    for key, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {key}: {status}")

    all_passed = all(results.values())
    print(f"\n最终结果: {'全部通过 ✓' if all_passed else '存在失败 ✗'}")
    print("=" * 60)

    return all_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
