"""
Unit tests for Python Execution Tool.
"""
import pytest
from app.agent.tools.python_exec_tool import PythonExecTool
from app.models.permission import PermissionContext


@pytest.fixture
def tool():
    return PythonExecTool()


@pytest.fixture
def permission():
    return PermissionContext(user_id="test_user", role="user")


@pytest.mark.asyncio
async def test_simple_calculation(tool, permission):
    """Test simple arithmetic calculation."""
    params = {
        "code": "result = 10 + 20"
    }
    result = await tool.execute(params, permission)

    assert result.status.value == "success"
    assert result.data["result"] == 30


@pytest.mark.asyncio
async def test_percentage_calculation(tool, permission):
    """Test percentage calculation."""
    params = {
        "code": "result = round((12000 - 10000) / 10000 * 100, 2)"
    }
    result = await tool.execute(params, permission)

    assert result.status.value == "success"
    assert result.data["result"] == 20.0


@pytest.mark.asyncio
async def test_with_context(tool, permission):
    """Test execution with injected context variables."""
    params = {
        "code": "result = sum(sales_data) / len(sales_data)",
        "context": {
            "sales_data": [100, 200, 300, 400, 500]
        }
    }
    result = await tool.execute(params, permission)

    assert result.status.value == "success"
    assert result.data["result"] == 300.0


@pytest.mark.asyncio
async def test_syntax_error(tool, permission):
    """Test handling of syntax errors."""
    params = {
        "code": "result = 10 +"
    }
    result = await tool.execute(params, permission)

    assert result.status.value == "failed"
    assert "Syntax error" in result.error


@pytest.mark.asyncio
async def test_name_error(tool, permission):
    """Test handling of undefined variables."""
    params = {
        "code": "result = undefined_variable * 2"
    }
    result = await tool.execute(params, permission)

    assert result.status.value == "failed"
    assert "Name error" in result.error
