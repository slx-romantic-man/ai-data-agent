"""
Unit tests for Analyzer Node
"""
import pytest
from unittest.mock import AsyncMock, patch
from app.agent.nodes.analyzer_node import analyzer_node, _extract_all_data
from app.agent.state import AgentState


@pytest.mark.asyncio
async def test_analyzer_node_with_data():
    """测试分析节点能够处理有效数据"""
    state: AgentState = {
        "messages": [],
        "query": "查询销售数据",
        "extracted_filters": {},
        "plan": [],
        "current_step": 0,
        "data_context": {
            "step_0_api_001": {
                "success": True,
                "data": [
                    {"region": "华东", "sales": 1000},
                    {"region": "华北", "sales": 800}
                ]
            }
        }
    }

    with patch("app.agent.nodes.analyzer_node.DataAnalyzer") as mock_analyzer_class:
        mock_analyzer = AsyncMock()
        mock_analyzer.analyze.return_value = {
            "analysis": "华东地区销售额最高，达到1000元",
            "analysis_type": "summary"
        }
        mock_analyzer_class.return_value = mock_analyzer

        result = await analyzer_node(state)

        assert len(result["messages"]) == 1
        assert result["messages"][0]["role"] == "assistant"
        assert "华东地区销售额最高" in result["messages"][0]["content"]
        assert result["messages"][0]["type"] == "analysis"


@pytest.mark.asyncio
async def test_analyzer_node_no_data():
    """测试分析节点处理无数据情况"""
    state: AgentState = {
        "messages": [],
        "query": "查询销售数据",
        "extracted_filters": {},
        "plan": [],
        "current_step": 0,
        "data_context": {}
    }

    result = await analyzer_node(state)

    assert len(result["messages"]) == 1
    assert "未能获取到有效数据" in result["messages"][0]["content"]


@pytest.mark.asyncio
async def test_analyzer_node_multiple_data_sources():
    """测试分析节点能够综合多个数据源"""
    state: AgentState = {
        "messages": [],
        "query": "综合分析",
        "extracted_filters": {},
        "plan": [],
        "current_step": 0,
        "data_context": {
            "step_0_api_001": {
                "success": True,
                "data": [{"region": "华东", "sales": 1000}]
            },
            "step_1_api_002": {
                "success": True,
                "data": [{"region": "华北", "sales": 800}]
            }
        }
    }

    with patch("app.agent.nodes.analyzer_node.DataAnalyzer") as mock_analyzer_class:
        mock_analyzer = AsyncMock()
        mock_analyzer.analyze.return_value = {
            "analysis": "综合分析报告",
            "analysis_type": "summary"
        }
        mock_analyzer_class.return_value = mock_analyzer

        result = await analyzer_node(state)

        # 验证调用了 analyze 并传入了合并后的数据
        mock_analyzer.analyze.assert_called_once()
        call_args = mock_analyzer.analyze.call_args
        assert len(call_args.kwargs["data"]) == 2


def test_extract_all_data():
    """测试数据提取函数"""
    data_context = {
        "step_0_api_001": {
            "success": True,
            "data": [{"id": 1}, {"id": 2}]
        },
        "step_1_api_002": {
            "success": True,
            "data": [{"id": 3}]
        },
        "step_2_failed": {
            "success": False,
            "error": "Failed"
        }
    }

    result = _extract_all_data(data_context)

    assert len(result) == 3
    assert {"id": 1} in result
    assert {"id": 2} in result
    assert {"id": 3} in result


def test_extract_all_data_with_dict():
    """测试提取字典类型数据"""
    data_context = {
        "step_0_api_001": {
            "success": True,
            "data": {"total": 100, "count": 5}
        }
    }

    result = _extract_all_data(data_context)

    assert len(result) == 1
    assert result[0] == {"total": 100, "count": 5}


def test_extract_all_data_empty():
    """测试空数据上下文"""
    result = _extract_all_data({})
    assert result == []
