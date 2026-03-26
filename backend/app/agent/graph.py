"""
LangGraph 工作流图定义
组装所有节点并配置边与路由逻辑
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.agent.state import AgentState
from app.agent.nodes.intent_node import intent_clarification_node
from app.agent.nodes.retrieval_node import retrieval_node as _retrieval_node
from app.agent.nodes.planner_node import planner_node as _planner_node
from app.agent.nodes.executor_node import executor_node
from app.agent.nodes.analyzer_node import analyzer_node
from app.models.permission import PermissionContext
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 全局变量存储检索结果
_retrieved_apis_cache = []
_retrieved_tables_cache = []


def should_continue_execution(state: AgentState) -> str:
    """判断 Executor 是否需要继续执行"""
    plan = state.get("plan") or []
    current_step = state.get("current_step", 0)

    if current_step < len(plan):
        return "executor"
    return "analyzer"


def should_require_approval(state: AgentState) -> str:
    """判断是否需要人工审批或权限检查失败"""
    # 检查是否有权限错误
    plan = state.get("plan") or []
    if not plan:
        # 计划为空，直接跳到 analyzer 返回错误
        return "analyzer"

    requires_approval = state.get("requires_approval", False)
    if requires_approval:
        return "approval_gate"
    return "executor"


def should_clarify(state: AgentState) -> str:
    """判断 Intent 节点后是否需要澄清"""
    extracted_filters = state.get("extracted_filters")

    if extracted_filters is None:
        return END
    return "retrieval"


async def create_graph(permission: PermissionContext):
    """
    创建 LangGraph 工作流图

    Args:
        permission: 用户权限上下文

    Returns:
        编译后的 LangGraph 图
    """

    async def retrieval_wrapper(state: AgentState) -> AgentState:
        """Retrieval 节点包装器，缓存检索结果"""
        global _retrieved_apis_cache, _retrieved_tables_cache
        result = await _retrieval_node(state)
        _retrieved_apis_cache = result.get("retrieved_apis", [])
        _retrieved_tables_cache = result.get("retrieved_tables", [])
        return state

    async def planner_wrapper(state: AgentState) -> AgentState:
        """Planner 节点包装器，传递缓存的检索结果和权限信息"""
        global _retrieved_apis_cache, _retrieved_tables_cache
        result = await _planner_node(
            state, _retrieved_apis_cache, _retrieved_tables_cache
        )

        # 检查 API 权限：预检查用户对所有 API 的访问权限
        plan = result.get("plan", [])
        api_steps = [
            step for step in plan if step.get("tool") == "api_fetch"
        ]

        if api_steps:
            from app.services.api_permission_service import (
                get_api_permission_service
            )
            from app.access.database.connection import get_db
            from app.access.database.models import APIConfig
            from sqlalchemy import select

            permission_service = await get_api_permission_service()

            # 检查每个 API 调用的权限
            for step in api_steps:
                api_id = step.get("api_id")
                if not api_id:
                    continue

                # 解析 API ID
                api_config_id_int = None
                try:
                    api_config_id_int = int(api_id)
                except (ValueError, TypeError):
                    db = await get_db()
                    async with db.get_session() as session:
                        api_result = await session.execute(
                            select(APIConfig).where(
                                APIConfig.config_id == api_id
                            )
                        )
                        api_record = api_result.scalar_one_or_none()
                        if api_record:
                            api_config_id_int = api_record.id

                # 检查权限
                if api_config_id_int:
                    user_permission = (
                        await permission_service.get_active_permission(
                            permission.user_id, api_config_id_int
                        )
                    )
                    if not user_permission:
                        # 无权限，直接拒绝
                        logger.warning(
                            f"User {permission.user_id} no permission "
                            f"for API {api_id}"
                        )
                        result["plan"] = []
                        result["error"] = (
                            f"你没有该 API 的使用权限，"
                            f"请联系管理员授权。API: {api_id}"
                        )
                        break

        # 不再需要审批流程
        result["requires_approval"] = False

        return result

    async def executor_wrapper(state: AgentState) -> AgentState:
        """Executor 节点包装器"""
        return await executor_node(state, permission)

    # 创建状态图
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("intent", intent_clarification_node)
    workflow.add_node("retrieval", retrieval_wrapper)
    workflow.add_node("planner", planner_wrapper)
    workflow.add_node("approval_gate", lambda state: state)
    workflow.add_node("executor", executor_wrapper)
    workflow.add_node("analyzer", analyzer_node)

    # 设置入口点
    workflow.set_entry_point("intent")

    # 配置边
    workflow.add_conditional_edges(
        "intent",
        should_clarify,
        {
            "retrieval": "retrieval",
            END: END
        }
    )

    workflow.add_edge("retrieval", "planner")

    workflow.add_conditional_edges(
        "planner",
        should_require_approval,
        {
            "executor": "executor",
            "approval_gate": "approval_gate",
            "analyzer": "analyzer"
        }
    )

    workflow.add_edge("approval_gate", "executor")

    workflow.add_conditional_edges(
        "executor",
        should_continue_execution,
        {
            "executor": "executor",
            "analyzer": "analyzer"
        }
    )

    workflow.add_edge("analyzer", END)

    # 初始化 AsyncSqliteSaver 用于状态持久化
    import os
    import aiosqlite
    os.makedirs("./data", exist_ok=True)

    # 创建数据库连接
    conn = aiosqlite.connect("./data/checkpoints.db")
    memory = AsyncSqliteSaver(conn)

    # 编译图（在 approval_gate 前中断）
    graph = workflow.compile(
        checkpointer=memory,
        interrupt_before=["approval_gate"]
    )

    logger.info("[Graph] LangGraph workflow compiled with AsyncSqliteSaver")
    return graph
