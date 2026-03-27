"""
F-06 测试 - 验证股票API返回结果规范化
"""
import asyncio
import json
from app.agent.tools.api_fetch_tool import get_api_fetch_tool
from app.models.permission import PermissionContext


async def test_normalized_stock_api():
    """测试规范化后的股票API返回格式"""
    tool = get_api_fetch_tool()

    permission = PermissionContext(
        user_id="admin",
        role="admin",
        conversation_id="test"
    )

    params = {
        "api_id": "alpha_vantage_stock",
        "endpoint": "获取日线数据",
        "params": {
            "symbol": "AAPL",
            "outputsize": "compact",
            "function": "TIME_SERIES_DAILY"
        }
    }

    result = await tool.execute(params, permission)

    print("=== API调用结果 ===")
    print(f"Success: {result.status}")
    if result.error:
        print(f"Error: {result.error}")
        return

    print(f"Data type: {type(result.data)}")

    if result.data:
        print(f"\n=== 规范化数据结构 ===")
        if isinstance(result.data, dict):
            print(f"Keys: {list(result.data.keys())}")
            print(f"Row count: {result.data.get('row_count', 0)}")
            print(f"Source: {result.data.get('source', 'N/A')}")
            print(f"Symbol: {result.data.get('symbol', 'N/A')}")

            rows = result.data.get("rows", [])
            if rows:
                print(f"\n第一条数据示例:")
                print(json.dumps(rows[0], indent=2))

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
            # 新增：处理规范化的股票数据格式
            if isinstance(data, dict) and "rows" in data:
                rows = data.get("rows", [])
                if isinstance(rows, list):
                    all_data.extend(rows)
            elif isinstance(data, list):
                all_data.extend(data)
            elif isinstance(data, dict):
                all_data.append(data)

    print(f"Extracted rows: {len(all_data)}")
    print(f"SUCCESS: Analyzer can now extract {len(all_data)} trading day rows")

    # 验证数据结构
    if all_data:
        first_row = all_data[0]
        print(f"\n=== Data Field Validation ===")
        required_fields = ["date", "open", "high", "low", "close", "volume"]
        for field in required_fields:
            status = "PASS" if field in first_row else "FAIL"
            print(f"{status} {field}: {first_row.get(field, 'MISSING')}")

        if "pct_change" in first_row:
            print(f"PASS pct_change: {first_row['pct_change']:.2f}%")

    await tool.close()


if __name__ == "__main__":
    asyncio.run(test_normalized_stock_api())
