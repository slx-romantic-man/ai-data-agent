"""
F-11 测试：Executor数据存储键标准化与结果完整性
验证data_context的key命名规范和value结构完整性
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from app.agent.nodes.executor_node import executor_node
from app.agent.state import AgentState
from app.models.permission import PermissionContext


async def test_executor_key_format():
    """测试1: 验证data_context的key格式符合step_<index>_<api_id>规范"""
    print("\n=== Test 1: Executor Key Format ===")

    # 模拟一个包含股票API调用的plan
    state = AgentState(
        query="查询AAPL股票",
        plan=[
            {
                "step": 1,
                "tool": "api_fetch",
                "api_id": "stock_alpha_vantage",
                "params": {
                    "endpoint": "time_series_daily",
                    "params": {"symbol": "AAPL"}
                },
                "description": "获取AAPL股票数据"
            }
        ],
        current_step=0,
        data_context={},
        messages=[]
    )

    permission = PermissionContext(user_id="1", role="employee")

    # 执行
    result_state = await executor_node(state, permission)

    # 验证key格式
    data_context = result_state.get("data_context", {})
    print(f"Data context keys: {list(data_context.keys())}")

    expected_key = "step_0_stock_alpha_vantage"
    if expected_key in data_context:
        print(f"[PASS] Key format correct: {expected_key}")

        # 验证value结构
        value = data_context[expected_key]
        print(f"Value structure: {list(value.keys())}")

        required_fields = ["success", "data", "metadata"]
        missing = [f for f in required_fields if f not in value]
        if not missing:
            print(f"[PASS] Value contains all required fields: {required_fields}")
        else:
            print(f"[FAIL] Missing fields: {missing}")

        # 检查data字段是否包含原始响应和标准化结果
        if value.get("success") and value.get("data"):
            data = value["data"]
            print(f"Data type: {type(data)}")
            if isinstance(data, dict):
                print(f"Data keys: {list(data.keys())}")
                if "rows" in data:
                    print(f"[PASS] Data contains standardized 'rows' field")
                    print(f"  Row count: {data.get('row_count', 0)}")
                else:
                    print(f"[FAIL] Data missing 'rows' field")
    else:
        print(f"[FAIL] Expected key not found: {expected_key}")
        print(f"  Available keys: {list(data_context.keys())}")


async def test_analyzer_can_extract():
    """测试2: 验证Analyzer能从标准化的data_context中提取数据"""
    print("\n=== Test 2: Analyzer Extraction ===")

    from app.agent.nodes.analyzer_node import _extract_all_data

    # 模拟executor存储的标准格式
    data_context = {
        "step_0_stock_alpha_vantage": {
            "success": True,
            "data": {
                "rows": [
                    {"date": "2024-01-01", "close": 150.0, "open": 148.0},
                    {"date": "2024-01-02", "close": 152.0, "open": 150.0}
                ],
                "row_count": 2,
                "source": "alpha_vantage"
            },
            "metadata": {}
        }
    }

    extracted = _extract_all_data(data_context)
    print(f"Extracted rows: {len(extracted)}")

    if len(extracted) == 2:
        print(f"[PASS] Analyzer correctly extracted {len(extracted)} rows")
        print(f"  Sample row: {extracted[0]}")
    else:
        print(f"[FAIL] Expected 2 rows, got {len(extracted)}")


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("F-11: Executor数据存储键标准化测试")
    print("=" * 60)

    await test_executor_key_format()
    await test_analyzer_can_extract()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
