"""
Unit tests for Planner Node
"""
import pytest
from app.agent.nodes.planner_node import planner_node
from app.agent.state import AgentState


@pytest.mark.asyncio
async def test_planner_node_generates_valid_plan():
    """测试 Planner Node 能够生成有效的执行计划"""
    # 准备测试数据
    state: AgentState = {
        "messages": [],
        "query": "查询华东地区最近7天的销售数据",
        "extracted_filters": {
            "intent_type": "api_query",
            "entities": {
                "time_range": {"start": "2024-01-01", "end": "2024-01-07"},
                "location": "华东"
            },
            "metrics": ["销售额"],
            "dimensions": ["日期"],
            "confidence": 0.9
        },
        "plan": None,
        "current_step": 0,
        "data_context": {}
    }

    retrieved_apis = [
        {
            "api_id": "sales_daily",
            "description": "查询每日销售数据",
            "params": {"start_date": "string", "end_date": "string", "region": "string"}
        },
        {
            "api_id": "sales_summary",
            "description": "销售汇总统计",
            "params": {"date_range": "string"}
        }
    ]

    # 执行节点
    result_state = await planner_node(state, retrieved_apis)

    # 验证结果
    assert result_state["plan"] is not None, "Plan should not be None"
    assert isinstance(result_state["plan"], list), "Plan should be a list"
    assert len(result_state["plan"]) > 0, "Plan should have at least one step"
    assert result_state["current_step"] == 0, "current_step should be reset to 0"

    # 验证第一个步骤的结构
    first_step = result_state["plan"][0]
    assert "step_id" in first_step
    assert "tool" in first_step
    assert "description" in first_step
    assert first_step["tool"] in ["api_fetch", "sql_query"]


@pytest.mark.asyncio
async def test_planner_node_handles_empty_apis():
    """测试 Planner Node 处理空 API 列表的情况"""
    state: AgentState = {
        "messages": [],
        "query": "查询数据",
        "extracted_filters": {},
        "plan": None,
        "current_step": 0,
        "data_context": {}
    }

    retrieved_apis = []

    # 执行节点
    result_state = await planner_node(state, retrieved_apis)

    # 应该返回空计划或降级计划
    assert result_state["plan"] is not None
    assert result_state["current_step"] == 0


@pytest.mark.asyncio
async def test_planner_node_plan_structure():
    """测试生成的计划结构符合预期"""
    state: AgentState = {
        "messages": [],
        "query": "分析上海地区的销售趋势",
        "extracted_filters": {
            "entities": {"location": "上海"},
            "metrics": ["销售额"]
        },
        "plan": None,
        "current_step": 0,
        "data_context": {}
    }

    retrieved_apis = [
        {
            "api_id": "sales_api",
            "description": "销售数据API",
            "params": {"region": "string"}
        }
    ]

    result_state = await planner_node(state, retrieved_apis)

    # 验证计划中的每个步骤都有必需字段
    for step in result_state["plan"]:
        assert "step_id" in step
        assert "tool" in step
        assert "params" in step
        assert "description" in step
        assert "depends_on" in step
        assert isinstance(step["params"], dict)
        assert isinstance(step["depends_on"], list)
