"""
端到端测试：数学运算场景 (F-19)
测试 Python 代码执行能力在实际工作流中的表现
"""
import pytest
from app.agent.state import AgentState
from app.agent.graph import create_graph
from app.models.permission import PermissionContext


@pytest.mark.asyncio
async def test_scenario_1_simple_calculation():
    """场景1：简单计算 - 上个月销售额10000，这个月12000，增长率是多少"""
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

    config = {"configurable": {"thread_id": "test_math_scenario_1"}}

    final_state = None
    async for event in graph.astream(initial_state, config):
        if "__end__" in event:
            final_state = event["__end__"]

    assert final_state is not None
    assert "plan" in final_state
    assert len(final_state["plan"]) > 0

    # 验证生成了 python_exec 步骤
    has_python_exec = any(step.get("tool") == "python_exec" for step in final_state["plan"])
    assert has_python_exec, "计划中应包含 python_exec 步骤"

    # 验证计算结果
    assert "data_context" in final_state
    python_results = [v for k, v in final_state["data_context"].items() if "python_exec" in k]
    assert len(python_results) > 0, "应该有 Python 执行结果"

    # 验证增长率计算正确 (20%)
    result_str = str(python_results[0])
    assert "20" in result_str or "0.2" in result_str, f"结果应包含 20% 或 0.2，实际: {result_str}"


@pytest.mark.asyncio
async def test_scenario_2_api_then_calculation():
    """场景2：基于API数据计算 - 最近7天订单数据的平均订单金额"""
    permission = PermissionContext(user_id="admin_001", role="admin")
    graph = await create_graph(permission)

    initial_state: AgentState = {
        "messages": [],
        "query": "最近7天订单数据的平均订单金额是多少",
        "extracted_filters": {"time_range": "last_7_days"},
        "plan": [],
        "current_step": 0,
        "data_context": {},
        "permission": {"user_id": "admin_001", "role": "admin"}
    }

    config = {"configurable": {"thread_id": "test_math_scenario_2"}}

    final_state = None
    async for event in graph.astream(initial_state, config):
        if "__end__" in event:
            final_state = event["__end__"]

    assert final_state is not None

    # 验证计划包含 api_fetch 和 python_exec
    plan = final_state.get("plan", [])
    has_api = any(step.get("tool") == "api_fetch" for step in plan)
    has_python = any(step.get("tool") == "python_exec" for step in plan)

    assert has_api, "应包含 API 调用步骤"
    assert has_python, "应包含 Python 计算步骤"

    # 验证执行结果存在
    assert len(final_state["data_context"]) > 0, "应有数据存储"


@pytest.mark.asyncio
async def test_scenario_3_multi_step_dependency():
    """场景3：多步骤依赖 - 销售数据和成本数据的利润率"""
    permission = PermissionContext(user_id="admin_001", role="admin")
    graph = await create_graph(permission)

    initial_state: AgentState = {
        "messages": [],
        "query": "计算本月销售额和成本的利润率",
        "extracted_filters": {"time_range": "this_month"},
        "plan": [],
        "current_step": 0,
        "data_context": {},
        "permission": {"user_id": "admin_001", "role": "admin"}
    }

    config = {"configurable": {"thread_id": "test_math_scenario_3"}}

    final_state = None
    async for event in graph.astream(initial_state, config):
        if "__end__" in event:
            final_state = event["__end__"]

    assert final_state is not None

    # 验证多步骤计划
    plan = final_state.get("plan", [])
    assert len(plan) >= 2, "应包含至少2个步骤"

    # 验证包含多个数据获取和计算
    api_steps = [s for s in plan if s.get("tool") == "api_fetch"]
    python_steps = [s for s in plan if s.get("tool") == "python_exec"]

    assert len(api_steps) >= 1, "应至少有1个 API 调用"
    assert len(python_steps) >= 1, "应至少有1个 Python 计算"
