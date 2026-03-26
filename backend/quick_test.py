"""快速测试场景3"""
import asyncio
from app.agent.graph import create_graph
from app.agent.state import AgentState
from app.models.permission import PermissionContext


async def main():
    print("测试场景3：多步骤依赖")

    permission = PermissionContext(user_id="admin_001", role="admin")
    graph = await create_graph(permission)

    initial_state: AgentState = {
        "messages": [],
        "query": "计算本月销售额和成本的利润率",
        "extracted_filters": {},
        "plan": [],
        "current_step": 0,
        "data_context": {},
        "permission": {"user_id": "admin_001", "role": "admin"}
    }

    config = {"configurable": {"thread_id": "quick_test"}}

    final_state = None
    async for event in graph.astream(initial_state, config):
        if "__end__" in event:
            final_state = event["__end__"]

    if final_state:
        plan = final_state.get("plan", [])
        print(f"\n生成的计划步骤数: {len(plan)}")
        for i, step in enumerate(plan):
            print(f"步骤{i+1}: {step.get('tool')} - {step.get('description', '')}")
            if step.get('tool') == 'python_exec':
                code = step.get('params', {}).get('code', '')
                print(f"  代码: {code[:100]}...")

        print(f"\n数据上下文键: {list(final_state.get('data_context', {}).keys())}")

        python_results = [v for k, v in final_state.get("data_context", {}).items() if "python_exec" in k]
        if python_results:
            print(f"\nPython执行结果: {python_results[0]}")

        has_python = any(s.get("tool") == "python_exec" for s in plan)
        success = has_python and len(plan) >= 2
        print(f"\n测试结果: {'通过' if success else '失败'}")
        return success

    return False


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)
