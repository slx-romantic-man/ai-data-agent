"""手动测试数学运算场景"""
import asyncio
from app.agent.graph import create_graph
from app.agent.state import AgentState
from app.models.permission import PermissionContext


async def test_scenario_1():
    """场景1：简单计算"""
    print("\n" + "="*60)
    print("场景1：简单计算 - 上个月销售额10000，这个月12000，增长率是多少")
    print("="*60)

    permission = PermissionContext(user_id="admin_001", role="admin")
    graph = await create_graph(permission)

    initial_state: AgentState = {
        "messages": [],
        "query": "上个月销售额10000，这个月12000，增长率是多少",
        "extracted_filters": {},
        "plan": [],
        "current_step": 0,
        "data_context": {},
        "permission": {"user_id": "admin_001", "role": "admin"}
    }

    config = {"configurable": {"thread_id": "manual_test_1"}}

    final_state = None
    async for event in graph.astream(initial_state, config):
        node_name = list(event.keys())[0] if event else None
        if node_name and node_name != "__end__":
            print(f"\n[{node_name}] 执行中...")
            final_state = event[node_name]
        if "__end__" in event:
            final_state = event["__end__"]

    if not final_state:
        print("\n❌ 错误：未获取到最终状态")
        return False

    print("\n--- 最终计划 ---")
    for i, step in enumerate(final_state.get("plan", [])):
        print(f"步骤 {i+1}: {step.get('tool')} - {step.get('description', '')}")

    print("\n--- 数据上下文 ---")
    for key, value in final_state.get("data_context", {}).items():
        print(f"{key}: {value}")

    # 验证
    has_python = any(s.get("tool") == "python_exec" for s in final_state.get("plan", []))
    print(f"\n[OK] 包含 python_exec: {has_python}")

    python_results = [v for k, v in final_state.get("data_context", {}).items() if "python_exec" in k]
    if python_results:
        print(f"[OK] Python 执行结果: {python_results[0]}")

    return has_python and len(python_results) > 0


async def test_scenario_2():
    """场景2：API + 计算"""
    print("\n" + "="*60)
    print("场景2：API + 计算 - 最近7天订单数据的平均订单金额")
    print("="*60)

    permission = PermissionContext(user_id="admin_001", role="admin")
    graph = await create_graph(permission)

    initial_state: AgentState = {
        "messages": [],
        "query": "最近7天订单数据的平均订单金额是多少",
        "extracted_filters": {},
        "plan": [],
        "current_step": 0,
        "data_context": {},
        "permission": {"user_id": "admin_001", "role": "admin"}
    }

    config = {"configurable": {"thread_id": "manual_test_2"}}

    final_state = None
    async for event in graph.astream(initial_state, config):
        node_name = list(event.keys())[0] if event else None
        if node_name and node_name != "__end__":
            print(f"\n[{node_name}] 执行中...")
            final_state = event[node_name]
        if "__end__" in event:
            final_state = event["__end__"]

    if not final_state:
        print("\n❌ 错误：未获取到最终状态")
        return False

    print("\n--- 最终计划 ---")
    for i, step in enumerate(final_state.get("plan", [])):
        print(f"步骤 {i+1}: {step.get('tool')} - {step.get('description', '')}")

    print("\n--- 数据上下文 ---")
    for key, value in final_state.get("data_context", {}).items():
        print(f"{key}: {str(value)[:100]}...")

    plan = final_state.get("plan", [])
    has_api = any(s.get("tool") == "api_fetch" for s in plan)
    has_python = any(s.get("tool") == "python_exec" for s in plan)

    print(f"\n[OK] 包含 api_fetch: {has_api}")
    print(f"[OK] 包含 python_exec: {has_python}")

    return has_api and has_python


async def test_scenario_3():
    """场景3：多步骤依赖"""
    print("\n" + "="*60)
    print("场景3：多步骤依赖 - 计算本月销售额和成本的利润率")
    print("="*60)

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

    config = {"configurable": {"thread_id": "manual_test_3"}}

    final_state = None
    async for event in graph.astream(initial_state, config):
        node_name = list(event.keys())[0] if event else None
        if node_name and node_name != "__end__":
            print(f"\n[{node_name}] 执行中...")
            final_state = event[node_name]
        if "__end__" in event:
            final_state = event["__end__"]

    if not final_state:
        print("\n❌ 错误：未获取到最终状态")
        return False

    print("\n--- 最终计划 ---")
    for i, step in enumerate(final_state.get("plan", [])):
        print(f"步骤 {i+1}: {step.get('tool')} - {step.get('description', '')}")

    print("\n--- 数据上下文 ---")
    for key, value in final_state.get("data_context", {}).items():
        print(f"{key}: {str(value)[:100]}...")

    plan = final_state.get("plan", [])
    has_python = any(s.get("tool") == "python_exec" for s in plan)

    print(f"\n[OK] 包含 python_exec: {has_python}")
    print(f"[OK] 计划步骤数: {len(plan)}")

    return has_python and len(plan) >= 2


async def main():
    results = []

    results.append(await test_scenario_1())
    results.append(await test_scenario_2())
    results.append(await test_scenario_3())

    print(f"\n{'='*60}")
    print(f"总体结果: {sum(results)}/3 通过")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
