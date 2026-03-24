"""
Unit tests for Intent Clarification Node.
"""
import pytest
import asyncio
from app.agent.nodes.intent_node import intent_clarification_node
from app.agent.state import AgentState


@pytest.mark.asyncio
async def test_intent_node_with_complete_query():
    """测试完备查询：应提取 extracted_filters"""
    state: AgentState = {
        "messages": [],
        "query": "查询最近7天北京地区的销售额",
        "extracted_filters": None,
        "plan": None,
        "current_step": 0,
        "data_context": {}
    }

    result = await intent_clarification_node(state)

    # 验证 extracted_filters 被正确提取
    assert result["extracted_filters"] is not None
    assert "intent_type" in result["extracted_filters"]
    assert "entities" in result["extracted_filters"]
    assert len(result["messages"]) == 0  # 不应有反问消息


@pytest.mark.asyncio
async def test_intent_node_with_incomplete_query():
    """测试不完备查询：应返回反问"""
    state: AgentState = {
        "messages": [],
        "query": "查询IP归属地",
        "extracted_filters": None,
        "plan": None,
        "current_step": 0,
        "data_context": {}
    }

    result = await intent_clarification_node(state)

    # 验证返回了反问消息
    assert len(result["messages"]) > 0
    assert result["messages"][0]["type"] == "clarification"
    assert "IP" in result["messages"][0]["content"] or "地址" in result["messages"][0]["content"]
    assert result["extracted_filters"] is None


@pytest.mark.asyncio
async def test_intent_node_state_structure():
    """测试节点输入输出的状态结构正确性"""
    state: AgentState = {
        "messages": [],
        "query": "查询本月订单量",
        "extracted_filters": None,
        "plan": None,
        "current_step": 0,
        "data_context": {}
    }

    result = await intent_clarification_node(state)

    # 验证返回的状态包含所有必需字段
    assert "messages" in result
    assert "query" in result
    assert "extracted_filters" in result
    assert "plan" in result
    assert "current_step" in result
    assert "data_context" in result


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_intent_node_with_complete_query())
    asyncio.run(test_intent_node_with_incomplete_query())
    asyncio.run(test_intent_node_state_structure())
    print("✅ All tests passed!")
