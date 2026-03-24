"""
测试 Executor Node
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agent.nodes.executor_node import executor_node
from app.agent.state import AgentState
from app.models.permission import PermissionContext
from app.models.tool import ToolResult, ToolStatus


@pytest.fixture
def mock_permission():
    """模拟权限上下文"""
    permission = MagicMock(spec=PermissionContext)
    permission.user_id = "test_user"
    permission.role = "analyst"
    return permission


@pytest.fixture
def base_state():
    """基础状态"""
    return {
        "messages": [],
        "query": "test query",
        "extracted_filters": {},
        "plan": [],
        "current_step": 0,
        "data_context": {}
    }


@pytest.mark.asyncio
async def test_executor_node_sql_query(mock_permission, base_state):
    """测试执行 SQL 查询步骤"""
    # 准备计划
    base_state["plan"] = [
        {
            "step_id": 1,
            "tool": "sql_query",
            "api_id": "",
            "params": {"sql": "SELECT * FROM sales"},
            "description": "查询销售数据"
        }
    ]

    # Mock SQL 工具
    mock_tool = AsyncMock()
    mock_tool.execute.return_value = ToolResult(
        tool_name="sql_query",
        status=ToolStatus.SUCCESS,
        data={"data": [{"id": 1, "amount": 100}], "row_count": 1},
        metadata={"table": "sales"}
    )

    with patch("app.agent.nodes.executor_node.get_sql_query_tool", return_value=mock_tool):
        result_state = await executor_node(base_state, mock_permission)

    # 验证状态更新
    assert result_state["current_step"] == 1
    assert "step_0_sql_query" in result_state["data_context"]
    assert result_state["data_context"]["step_0_sql_query"]["success"] is True
    assert result_state["data_context"]["step_0_sql_query"]["data"]["row_count"] == 1


@pytest.mark.asyncio
async def test_executor_node_api_fetch(mock_permission, base_state):
    """测试执行 API 获取步骤"""
    # 准备计划
    base_state["plan"] = [
        {
            "step_id": 1,
            "tool": "api_fetch",
            "api_id": "inv_001",
            "params": {"endpoint": "query", "params": {"id": "123"}},
            "description": "查询库存数据"
        }
    ]

    # Mock API 工具
    mock_tool = MagicMock()
    mock_tool.execute = AsyncMock(return_value=ToolResult(
        tool_name="api_fetch",
        status=ToolStatus.SUCCESS,
        data={"items": [{"sku": "A001", "stock": 50}]},
        metadata={"api_id": "inv_001"}
    ))

    with patch("app.agent.nodes.executor_node.get_api_fetch_tool", return_value=mock_tool):
        result_state = await executor_node(base_state, mock_permission)

    # 验证状态更新
    assert result_state["current_step"] == 1
    assert "step_0_inv_001" in result_state["data_context"]
    assert result_state["data_context"]["step_0_inv_001"]["success"] is True


@pytest.mark.asyncio
async def test_executor_node_multiple_steps(mock_permission, base_state):
    """测试多步骤执行"""
    # 准备两步计划
    base_state["plan"] = [
        {
            "step_id": 1,
            "tool": "sql_query",
            "api_id": "",
            "params": {"sql": "SELECT * FROM sales"},
            "description": "查询销售数据"
        },
        {
            "step_id": 2,
            "tool": "api_fetch",
            "api_id": "inv_001",
            "params": {},
            "description": "查询库存数据"
        }
    ]

    # Mock 工具
    mock_sql_tool = AsyncMock()
    mock_sql_tool.execute.return_value = ToolResult(
        tool_name="sql_query",
        status=ToolStatus.SUCCESS,
        data={"data": []}
    )

    mock_api_tool = MagicMock()
    mock_api_tool.execute = AsyncMock(return_value=ToolResult(
        tool_name="api_fetch",
        status=ToolStatus.SUCCESS,
        data={"items": []}
    ))

    with patch("app.agent.nodes.executor_node.get_sql_query_tool", return_value=mock_sql_tool), \
         patch("app.agent.nodes.executor_node.get_api_fetch_tool", return_value=mock_api_tool):

        # 执行第一步
        state_after_step1 = await executor_node(base_state, mock_permission)
        assert state_after_step1["current_step"] == 1
        assert len(state_after_step1["data_context"]) == 1

        # 执行第二步
        state_after_step2 = await executor_node(state_after_step1, mock_permission)
        assert state_after_step2["current_step"] == 2
        assert len(state_after_step2["data_context"]) == 2


@pytest.mark.asyncio
async def test_executor_node_no_plan(mock_permission, base_state):
    """测试空计划"""
    base_state["plan"] = []

    result_state = await executor_node(base_state, mock_permission)

    # 状态不应改变
    assert result_state["current_step"] == 0
    assert len(result_state["data_context"]) == 0


@pytest.mark.asyncio
async def test_executor_node_step_out_of_range(mock_permission, base_state):
    """测试步骤索引超出范围"""
    base_state["plan"] = [{"step_id": 1, "tool": "sql_query", "params": {}}]
    base_state["current_step"] = 1  # 已经超出范围

    result_state = await executor_node(base_state, mock_permission)

    # 状态不应改变
    assert result_state["current_step"] == 1


@pytest.mark.asyncio
async def test_executor_node_unknown_tool(mock_permission, base_state):
    """测试未知工具类型"""
    base_state["plan"] = [
        {
            "step_id": 1,
            "tool": "unknown_tool",
            "api_id": "",
            "params": {},
            "description": "未知工具"
        }
    ]

    result_state = await executor_node(base_state, mock_permission)

    # 应该记录错误
    assert result_state["current_step"] == 1
    assert "step_0_unknown_tool" in result_state["data_context"]
    assert result_state["data_context"]["step_0_unknown_tool"]["success"] is False


@pytest.mark.asyncio
async def test_executor_node_tool_execution_error(mock_permission, base_state):
    """测试工具执行失败"""
    base_state["plan"] = [
        {
            "step_id": 1,
            "tool": "sql_query",
            "api_id": "",
            "params": {"sql": "INVALID SQL"},
            "description": "错误的SQL"
        }
    ]

    # Mock 工具返回失败
    mock_tool = AsyncMock()
    mock_tool.execute.return_value = ToolResult(
        tool_name="sql_query",
        status=ToolStatus.FAILED,
        error="SQL syntax error"
    )

    with patch("app.agent.nodes.executor_node.get_sql_query_tool", return_value=mock_tool):
        result_state = await executor_node(base_state, mock_permission)

    # 验证错误被记录
    assert result_state["current_step"] == 1
    assert result_state["data_context"]["step_0_sql_query"]["success"] is False
    assert "error" in result_state["data_context"]["step_0_sql_query"]
