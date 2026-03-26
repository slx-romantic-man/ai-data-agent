"""F-19 验证脚本 - 快速验证三个场景"""
import asyncio
from app.agent.graph import create_graph
from app.agent.state import AgentState
from app.models.permission import PermissionContext


async def verify_scenario(scenario_num, query, expected_tools):
    """验证单个场景"""
    print(f"\n{'='*60}")
    print(f"场景{scenario_num}: {query}")
    print(f"{'='*60}")

    permission = PermissionContext(user_id="admin_001", role="admin")
    graph = await create_graph(permission)

    initial_state: AgentState = {
        "messages": [],
        "query": query,
        "extracted_filters": {},
        "plan": [],
        "current_step": 0,
        "data_context": {},
        "permission": {"user_id": "admin_001", "role": "admin"}
    }

    config = {"configurable": {"thread_id": f"verify_s{scenario_num}"}}

    final_state = None
    async for event in graph.astream(initial_state, config):
        if "__end__" in event:
            final_state = event["__end__"]
        elif event:
            node = list(event.keys())[0]
            final_state = event[node]

    if not final_state:
        print("❌ 未获取到状态")
        return False

    plan = final_state.get("plan", [])
    tools_used = [s.get("tool") for s in plan]

    print(f"生成的工具序列: {tools_used}")
    print(f"期望包含: {expected_tools}")

    success = all(tool in tools_used for tool in expected_tools)
    print(f"结果: {'通过' if success else '失败'}")

    return success


async def main():
    results = []

    # 场景1：简单计算
    results.append(await verify_scenario(
        1,
        "上个月销售额10000，这个月12000，增长率是多少",
        ["python_exec"]
    ))

    # 场景2：API + 计算
    results.append(await verify_scenario(
        2,
        "最近7天订单数据的平均订单金额是多少",
        ["api_fetch", "python_exec"]
    ))

    # 场景3：多步骤
    results.append(await verify_scenario(
        3,
        "计算本月销售额和成本的利润率",
        ["python_exec"]  # 至少要有计算
    ))

    print(f"\n{'='*60}")
    print(f"总体结果: {sum(results)}/3 通过")
    print(f"{'='*60}")

    return all(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
