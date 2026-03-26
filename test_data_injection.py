#!/usr/bin/env python3
"""Test executor_node with data injection from data_context"""
import asyncio
import sys
sys.path.insert(0, 'backend')

from app.agent.nodes.executor_node import executor_node
from app.agent.state import AgentState
from app.models.permission import PermissionContext

async def test_data_injection():
    """Test python_exec with data injection from previous steps"""

    # Simulate state with previous API fetch results
    state: AgentState = {
        "messages": [],
        "query": "计算平均值",
        "extracted_filters": {},
        "plan": [
            {
                "step_id": "step_1",
                "tool": "python_exec",
                "params": {
                    "code": "data = step_0_api_001\nresult = sum([row['amount'] for row in data]) / len(data)"
                },
                "description": "计算订单平均金额"
            }
        ],
        "current_step": 0,
        "data_context": {
            "step_0_api_001": {
                "success": True,
                "data": [
                    {"order_id": 1, "amount": 100},
                    {"order_id": 2, "amount": 200},
                    {"order_id": 3, "amount": 300}
                ]
            }
        }
    }

    permission = PermissionContext(
        user_id="test_user",
        role="admin",
        allowed_apis=[]
    )

    print("Testing data injection from data_context...")
    print(f"Pre-existing data_context: {list(state['data_context'].keys())}")

    result_state = await executor_node(state, permission)

    print(f"\nAfter execution:")
    print(f"  current_step: {result_state['current_step']}")

    exec_result = result_state['data_context']['step_0_python_exec']
    print(f"  success: {exec_result['success']}")
    print(f"  result: {exec_result['data']['result']}")

    # Verify
    assert exec_result['success'], "Execution should succeed"
    assert exec_result['data']['result'] == 200.0, f"Average should be 200.0, got: {exec_result['data']['result']}"

    print("\nPASS: Data injection works correctly!")
    print(f"Calculated average: {exec_result['data']['result']}")

if __name__ == "__main__":
    asyncio.run(test_data_injection())
