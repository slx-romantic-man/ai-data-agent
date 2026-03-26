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
    print(f"\n✅ 包含 python_exec: {has_python}")

    python_results = [v for k, v in final_state.get("data_context", {}).items() if "python_exec" in k]
    if python_results:
        print(f"✅ Python 执行结果: {python_results[0]}")

    return has_python and len(python_results) > 0


async def main():
    success = await test_scenario_1()
    print(f"\n{'='*60}")
    print(f"测试结果: {'通过 ✅' if success else '失败 ❌'}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
