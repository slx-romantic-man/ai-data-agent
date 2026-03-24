"""
Unit tests for API Retrieval Node.
"""
import pytest
import asyncio
from app.agent.nodes.retrieval_node import retrieval_node
from app.agent.state import AgentState


@pytest.mark.asyncio
async def test_retrieval_node_returns_apis():
    """测试检索节点返回 API 列表"""
    state: AgentState = {
        "messages": [],
        "query": "查询IP归属地信息",
        "extracted_filters": None,
        "plan": None,
        "current_step": 0,
        "data_context": {}
    }

    result = await retrieval_node(state)

    # 验证返回了 retrieved_apis
    assert "retrieved_apis" in result
    assert isinstance(result["retrieved_apis"], list)


@pytest.mark.asyncio
async def test_retrieval_node_does_not_pollute_state():
    """测试检索节点不污染 AgentState"""
    state: AgentState = {
        "messages": [],
        "query": "查询销售数据",
        "extracted_filters": None,
        "plan": None,
        "current_step": 0,
        "data_context": {}
    }

    result = await retrieval_node(state)

    # 验证返回结果只包含 retrieved_apis，不包含 AgentState 字段
    assert "retrieved_apis" in result
    assert "messages" not in result
    assert "query" not in result
    assert "plan" not in result


@pytest.mark.asyncio
async def test_retrieval_node_api_format():
    """测试检索结果格式正确"""
    state: AgentState = {
        "messages": [],
        "query": "查询天气信息",
        "extracted_filters": None,
        "plan": None,
        "current_step": 0,
        "data_context": {}
    }

    result = await retrieval_node(state)

    # 验证 API 格式
    apis = result["retrieved_apis"]
    if len(apis) > 0:
        api = apis[0]
        assert "api_id" in api or "id" in api
        assert "name" in api or "api_name" in api


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_retrieval_node_returns_apis())
    asyncio.run(test_retrieval_node_does_not_pollute_state())
    asyncio.run(test_retrieval_node_api_format())
    print("✅ All tests passed!")
