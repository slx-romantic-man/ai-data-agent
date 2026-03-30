"""
Executor Node - 无脑执行机节点
遍历 plan 并根据 tool 字段路由到对应工具执行
"""
from typing import Dict, Any
from app.agent.state import AgentState
from app.agent.tools.sql_query_tool import get_sql_query_tool
from app.agent.tools.api_fetch_tool import get_api_fetch_tool
from app.agent.tools.python_exec_tool import get_python_exec_tool
from app.models.permission import PermissionContext
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def executor_node(state: AgentState, permission: PermissionContext) -> AgentState:
    """
    Executor Node: 执行当前步骤的工具调用

    Args:
        state: 当前 AgentState
        permission: 用户权限上下文

    Returns:
        更新后的 AgentState，包含执行结果和递增的 current_step
    """
    plan = state.get("plan") or []
    current_step = state.get("current_step", 0)
    data_context = state.get("data_context", {})

    if not plan or current_step >= len(plan):
        logger.warning(f"[ExecutorNode] No more steps to execute (step {current_step}/{len(plan)})")
        return state

    step = plan[current_step]
    tool_name = step.get("tool")
    api_id = step.get("api_id", "")
    params = step.get("params", {})
    description = step.get("description", "")

    logger.info(f"[ExecutorNode] Executing step {current_step + 1}/{len(plan)}: {description}")

    # 路由到对应工具
    result = None
    if tool_name == "sql_query":
        result = await _execute_sql_query(params, permission)
    elif tool_name == "api_fetch":
        result = await _execute_api_fetch(api_id, params, permission)
    elif tool_name == "python_exec":
        result = await _execute_python_exec(params, data_context, permission)
    else:
        logger.error(f"[ExecutorNode] Unknown tool: {tool_name}")
        result = {"success": False, "error": f"Unknown tool: {tool_name}"}

    # 存储结果到 data_context，key 格式: step_{idx}_{api_id}
    context_key = f"step_{current_step}_{api_id or tool_name}"
    data_context[context_key] = result

    logger.info(f"[ExecutorNode] Stored result in data_context['{context_key}']")

    # 更新状态
    state["data_context"] = data_context
    state["current_step"] = current_step + 1

    return state


async def _execute_sql_query(params: Dict[str, Any], permission: PermissionContext) -> Dict[str, Any]:
    """执行 SQL 查询工具"""
    try:
        logger.info(f"[ExecutorNode] SQL params: {params}")
        tool = await get_sql_query_tool()
        result = await tool.execute(params, permission)

        from app.models.tool import ToolStatus
        success = result.status == ToolStatus.SUCCESS

        logger.info(f"[ExecutorNode] SQL result status: {result.status}, data rows: {len(result.data) if result.data else 0}")
        if not success:
            logger.error(f"[ExecutorNode] SQL error: {result.error}")

        return {
            "success": success,
            "data": result.data if success else None,
            "error": result.error if not success else None,
            "metadata": result.metadata
        }
    except Exception as e:
        logger.error(f"[ExecutorNode] SQL query failed: {e}")
        return {"success": False, "error": str(e)}


async def _execute_api_fetch(api_id: str, params: Dict[str, Any], permission: PermissionContext) -> Dict[str, Any]:
    """执行 API 获取工具"""
    try:
        tool = get_api_fetch_tool()

        # 构造工具参数
        tool_params = {"api_id": api_id, **params}

        result = await tool.execute(tool_params, permission)

        from app.models.tool import ToolStatus
        success = result.status == ToolStatus.SUCCESS

        if not success:
            logger.error(f"[ExecutorNode] API fetch failed: {result.error}")

        return {
            "success": success,
            "data": result.data if success else None,
            "error": result.error if not success else None,
            "metadata": result.metadata
        }
    except Exception as e:
        logger.error(f"[ExecutorNode] API fetch exception: {e}")
        return {"success": False, "error": str(e)}


async def _execute_python_exec(params: Dict[str, Any], data_context: Dict[str, Any], permission: PermissionContext) -> Dict[str, Any]:
    """执行 Python 代码工具"""
    try:
        tool = get_python_exec_tool()

        # 从 data_context 提取数据注入到执行上下文
        code = params.get("code", "")
        context = params.get("context", {})

        # 将 data_context 中的数据注入到执行环境
        for key, value in data_context.items():
            if isinstance(value, dict) and value.get("success") and value.get("data"):
                context[key] = value

        tool_params = {"code": code, "context": context}
        result = await tool.execute(tool_params, permission)

        from app.models.tool import ToolStatus
        success = result.status == ToolStatus.SUCCESS

        logger.info(f"[ExecutorNode] Python exec result: {result.data if success else result.error}")

        return {
            "success": success,
            "data": result.data if success else None,
            "error": result.error if not success else None,
            "metadata": result.metadata
        }
    except Exception as e:
        logger.error(f"[ExecutorNode] Python exec failed: {e}")
        return {"success": False, "error": str(e)}

