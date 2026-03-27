"""
F-11 真实API调用测试：验证API返回的实际数据格式
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from app.agent.tools.api_fetch_tool import get_api_fetch_tool
from app.models.permission import PermissionContext


async def test_real_stock_api():
    """测试真实的股票API调用，查看返回格式"""
    print("\n=== Real Stock API Call Test ===")

    tool = get_api_fetch_tool()
    permission = PermissionContext(user_id="1", role="employee")

    params = {
        "api_id": "alpha_vantage_stock",
        "endpoint": "获取日线数据",
        "params": {"symbol": "IBM", "function": "TIME_SERIES_DAILY"}
    }

    result = await tool.execute(params, permission)

    print(f"Result status: {result.status}")
    print(f"Result data type: {type(result.data)}")

    if result.data:
        if isinstance(result.data, dict):
            print(f"Data keys: {list(result.data.keys())}")
            if "rows" in result.data:
                print(f"[PASS] Data has 'rows' field")
                print(f"  Row count: {result.data.get('row_count', 0)}")
                if result.data.get('rows'):
                    print(f"  Sample row: {result.data['rows'][0]}")
            else:
                print(f"[FAIL] Data missing 'rows' field")
                print(f"  Actual data structure: {result.data}")
        else:
            print(f"[FAIL] Data is not a dict: {type(result.data)}")
    else:
        print(f"[FAIL] No data returned")
        print(f"Error: {result.error}")


if __name__ == "__main__":
    asyncio.run(test_real_stock_api())
