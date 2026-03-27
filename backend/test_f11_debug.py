"""
Debug test: Check why Analyzer extracts 0 rows in some cases
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from app.agent.nodes.executor_node import executor_node
from app.agent.nodes.analyzer_node import _extract_all_data
from app.agent.state import AgentState
from app.models.permission import PermissionContext
import json


async def debug_data_structure():
    """Debug: 查看实际存储的数据结构"""
    print("=== Debug: Data Structure Analysis ===\n")

    permission = PermissionContext(user_id="1", role="employee")

    state = AgentState(
        query="查询IBM股票数据",
        plan=[{
            "step": 1,
            "tool": "api_fetch",
            "api_id": "alpha_vantage_stock",
            "params": {
                "endpoint": "获取日线数据",
                "params": {"symbol": "IBM", "function": "TIME_SERIES_DAILY"}
            },
            "description": "获取IBM股票数据"
        }],
        current_step=0,
        data_context={},
        messages=[]
    )

    # Execute
    state = await executor_node(state, permission)
    data_context = state.get("data_context", {})

    print(f"Data context keys: {list(data_context.keys())}\n")

    for key, value in data_context.items():
        print(f"Key: {key}")
        print(f"  Type: {type(value)}")
        print(f"  Keys: {list(value.keys()) if isinstance(value, dict) else 'N/A'}")

        if isinstance(value, dict):
            print(f"  success: {value.get('success')}")
            print(f"  data type: {type(value.get('data'))}")

            data = value.get('data')
            if isinstance(data, dict):
                print(f"  data keys: {list(data.keys())}")
                if 'rows' in data:
                    print(f"  rows count: {len(data['rows'])}")
                    print(f"  rows type: {type(data['rows'])}")
                    if data['rows']:
                        print(f"  first row: {data['rows'][0]}")
            elif isinstance(data, list):
                print(f"  data is list with {len(data)} items")

    # Test extraction
    print("\n--- Testing _extract_all_data ---")
    extracted = _extract_all_data(data_context)
    print(f"Extracted rows: {len(extracted)}")

    if extracted:
        print(f"First extracted row: {extracted[0]}")


if __name__ == "__main__":
    asyncio.run(debug_data_structure())
