"""
F-06 测试 - 验证当前股票API返回问题
"""
import asyncio
import json
from app.agent.tools.api_fetch_tool import get_api_fetch_tool
from app.models.permission import PermissionContext

async def test_current_stock_api():
    """测试当前股票API返回格式"""
    tool = get_api_fetch_tool()

    permission = PermissionContext(
        user_id="admin",
        role="admin",
        conversation_id="test"
    )

    params = {
        "api_id": "alpha_vantage_stock",
        "endpoint": "get_stock",
        "params": {
            "symbol": "AAPL",
            "outputsize": "compact"
        }
    }

    result = await tool.execute(params, permission)

    print("=== API调用结果 ===")
    print(f"Success: {result.status}")
    print(f"Error: {result.error}")
    print(f"Data type: {type(result.data)}")

    if result.data:
        print(f"\nData keys: {list(result.data.keys()) if isinstance(result.data, dict) else 'Not a dict'}")
        print(f"\nFirst 500 chars of data:")
        print(json.dumps(result.data, indent=2)[:500])

    # 模拟Analyzer提取数据
    print("\n=== 模拟Analyzer提取 ===")
    data_context = {"step_0_alpha_vantage_stock": {
        "success": True,
        "data": result.data
    }}

    all_data = []
    for key, res in data_context.items():
        if res.get("success") and res.get("data"):
            data = res["data"]
            if isinstance(data, list):
                all_data.extend(data)
            elif isinstance(data, dict):
                all_data.append(data)

    print(f"Extracted rows: {len(all_data)}")
    print(f"问题：Analyzer期望提取多行交易日数据，但实际只提取到1个dict对象")

if __name__ == "__main__":
    asyncio.run(test_current_stock_api())
