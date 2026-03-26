#!/usr/bin/env python3
"""Direct test of executor_node with python_exec"""
import asyncio
import sys
sys.path.insert(0, 'backend')

from app.agent.nodes.executor_node import executor_node
from app.agent.state import AgentState
from app.models.permission import PermissionContext

async def test_python_exec():
    """Test executor_node with python_exec step"""

    # Create test state with a python_exec plan
    state: AgentState = {
        "messages": [],
        "query": "计算增长率",
        "extracted_filters": {},
        "plan": [
            {
                "step_id": "step_1",
                "tool": "python_exec",
                "params": {
                    "code": "old_sales = 10000\nnew_sales = 12000\nresult = ((new_sales - old_sales) / old_sales) * 100"
                },
                "description": "计算销售额增长率"
            }
        ],
        "current_step": 0,
        "data_context": {}
    }

    # Create permission context
    permission = PermissionContext(
        user_id="test_user",
        role="admin",
        allowed_apis=[]
    )

    print("Testing executor_node with python_exec...")
    print(f"Initial state: current_step={state['current_step']}, plan_length={len(state['plan'])}")

    # Execute
    result_state = await executor_node(state, permission)

    print(f"\nAfter execution:")
    print(f"  current_step: {result_state['current_step']}")
    print(f"  data_context keys: {list(result_state['data_context'].keys())}")

    # Check result
    if result_state['data_context']:
        for key, value in result_state['data_context'].items():
            print(f"\n  {key}:")
            print(f"    success: {value.get('success')}")
            if value.get('success'):
                print(f"    result: {value.get('data', {}).get('result')}")
            else:
                print(f"    error: {value.get('error')}")

    # Verify
    assert result_state['current_step'] == 1, "current_step should increment to 1"
    assert 'step_0_python_exec' in result_state['data_context'], "Should have step_0_python_exec in data_context"

    exec_result = result_state['data_context']['step_0_python_exec']
    assert exec_result['success'], f"Execution should succeed, got: {exec_result}"
    assert exec_result['data']['result'] == 20.0, f"Result should be 20.0, got: {exec_result['data']['result']}"

    print("\n✅ All assertions passed!")
    print(f"✅ Python exec calculated growth rate: {exec_result['data']['result']}%")

if __name__ == "__main__":
    asyncio.run(test_python_exec())
