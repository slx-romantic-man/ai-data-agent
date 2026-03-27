"""
Test complete stock query end-to-end
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.agent.graph import create_graph
from app.agent.state import AgentState
from app.models.permission import PermissionContext


async def test_stock_query():
    """Test: 查询IBM股票最近的数据"""
    print("\n" + "="*70)
    print("测试: 查询IBM股票最近的数据")
    print("="*70)

    permission = PermissionContext(user_id="admin", role="admin")
    graph = await create_graph(permission)

    initial_state = AgentState(
        query="查询IBM股票最近的数据",
        messages=[],
        data_context={},
        plan=[],
        current_step=0
    )

    try:
        final_state = await graph.ainvoke(
            initial_state,
            {"configurable": {"thread_id": "test_stock"}}
        )

        plan = final_state.get("plan", [])
        final_answer = final_state.get("final_answer", "")
        error = final_state.get("error", "")

        print("\n[Plan Generated]")
        if plan:
            for step in plan:
                print(f"  Step {step['step_id']}: {step['tool']}")
                print(f"    api_id: {step.get('api_id', 'N/A')}")
                print(f"    params: {step.get('params', {})}")
        else:
            print("  (empty)")

        print(f"\n[Final Answer]")
        print(final_answer if final_answer else "(empty)")

        if error:
            print(f"\n[Error]")
            print(error)

        # Validation
        if plan and len(plan) > 0:
            first_step = plan[0]
            params = first_step.get("params", {})

            if "endpoint" in params:
                print("\n[PASS] Plan includes endpoint parameter")
                if final_answer and "未能获取" not in final_answer:
                    print("[PASS] Got valid answer")
                    return True
                else:
                    print("[FAIL] Answer indicates no data")
                    return False
            else:
                print(f"\n[FAIL] Plan missing endpoint, params keys: {list(params.keys())}")
                return False
        else:
            print("\n[FAIL] No plan generated")
            return False

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_stock_query())
    sys.exit(0 if result else 1)
