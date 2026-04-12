"""
LangGraph 工作流图定义
组装所有节点并配置边与路由逻辑
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.agent.state import AgentState
from app.agent.nodes.retrieval_node import retrieval_node as _retrieval_node
from app.agent.nodes.intent_planner_node import intent_planner_node
from app.agent.nodes.executor_node import executor_node, execute_single_step
from app.agent.nodes.analyzer_node import analyzer_node
from app.models.permission import PermissionContext
from app.utils.logger import get_logger

import asyncio

logger = get_logger(__name__)

# 全局变量存储检索结果
_retrieved_apis_cache = []
_retrieved_tables_cache = []


def should_continue_to_executor(state: AgentState) -> str:
    """路由从 intent_planner: 去 executor、analyzer 还是直接结束（澄清场景）"""
    plan = state.get("plan") or []
    if not plan:
        # 检查是否是因为澄清而 plan 为空
        extracted_filters = state.get("extracted_filters")
        messages = state.get("messages", [])
        if extracted_filters is None and messages:
            last_msg = messages[-1]
            if isinstance(last_msg, dict) and last_msg.get("type") == "clarification":
                # 已生成澄清问题，直接结束，不进入 analyzer
                return "clarify"
        return "analyzer"
    return "executor"


def should_continue_execution(state: AgentState) -> str:
    """判断 Executor 是否需要继续执行"""
    plan = state.get("plan") or []
    completed_step_ids = set(state.get("completed_step_ids", []))

    # Check if there are any uncompleted steps
    remaining = [
        step for step in plan
        if step.get("step_id", 0) not in completed_step_ids
    ]

    if remaining:
        return "executor"
    return "analyzer"


def should_analyze_or_end(state: AgentState) -> str:
    """判断是否需要调用 analyzer LLM，或直接结束"""
    data_context = state.get("data_context", {})
    if not data_context:
        return END
    return "analyzer"


def should_clarify_or_continue(state: AgentState) -> str:
    """判断 Intent Planner 节点后是否需要澄清"""
    extracted_filters = state.get("extracted_filters")

    if extracted_filters is None:
        return END
    return "intent_planner"


async def create_graph(permission: PermissionContext):
    """
    创建 LangGraph 工作流图

    Args:
        permission: 用户权限上下文

    Returns:
        编译后的 LangGraph 图
    """

    async def retrieval_wrapper(state: AgentState) -> AgentState:
        """Retrieval 节点包装器，缓存检索结果到 state 中"""
        global _retrieved_apis_cache, _retrieved_tables_cache
        result = await _retrieval_node(state, permission)
        _retrieved_apis_cache = result.get("retrieved_apis", [])
        _retrieved_tables_cache = result.get("retrieved_tables", [])
        # 将检索结果存入 state，供 intent_planner 使用
        state["retrieved_apis"] = _retrieved_apis_cache
        state["retrieved_tables"] = _retrieved_tables_cache
        return state

    async def intent_planner_wrapper(state: AgentState) -> AgentState:
        """
        Combined Intent + Planner 节点包装器：
        单次 LLM 调用同时完成意图识别和执行计划生成。
        """
        global _retrieved_apis_cache, _retrieved_tables_cache
        result = await intent_planner_node(
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

        return result

    async def executor_wrapper(state: AgentState) -> AgentState:
        """
        Executor wrapper: find all ready steps, execute in parallel,
        aggregate results, and update completed_step_ids.
        """
        plan = state.get("plan") or []
        data_context = state.get("data_context", {})
        completed_step_ids = list(state.get("completed_step_ids", []))

        # Find all steps whose depends_on are fully satisfied
        ready_steps = []
        for index, step in enumerate(plan):
            step_id = step.get("step_id", index)
            if step_id in completed_step_ids:
                continue  # already completed
            depends_on = step.get("depends_on", [])
            if all(dep in completed_step_ids for dep in depends_on):
                ready_steps.append((index, step))

        if not ready_steps:
            # No ready steps but plan is not fully complete — shouldn't normally happen
            logger.warning("[ExecutorWrapper] No ready steps found, plan may have unresolvable dependencies")
            return state

        logger.info(
            f"[ExecutorWrapper] Executing {len(ready_steps)} step(s) in parallel: "
            f"step_ids={[s.get('step_id', i) for i, s in ready_steps]}"
        )

        # Execute all ready steps concurrently
        coros = [
            execute_single_step(step, index, data_context, permission)
            for index, step in ready_steps
        ]
        results = await asyncio.gather(*coros, return_exceptions=True)

        # Aggregate results into data_context
        for (context_key, execution_result, step_id), (index, step) in zip(results, ready_steps):
            if isinstance(execution_result, Exception):
                logger.error(f"[ExecutorWrapper] Step {step_id} raised exception: {execution_result}")
                execution_result = {"success": False, "error": str(execution_result)}
            data_context[context_key] = execution_result
            completed_step_ids.append(step_id)
            logger.info(f"[ExecutorWrapper] Completed step {step_id}, stored in data_context['{context_key}']")

        # Determine next current_step (first uncompleted step index, or len(plan) if done)
        next_step = None
        for i, step in enumerate(plan):
            sid = step.get("step_id", i)
            if sid not in completed_step_ids:
                next_step = i
                break
        if next_step is None:
            next_step = len(plan)

        state["data_context"] = data_context
        state["current_step"] = next_step
        state["completed_step_ids"] = completed_step_ids

        return state

    # 创建状态图
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("retrieval", retrieval_wrapper)
    workflow.add_node("intent_planner", intent_planner_wrapper)
    workflow.add_node("executor", executor_wrapper)
    workflow.add_node("analyzer", analyzer_node)

    # 设置入口点：先检索
    workflow.set_entry_point("retrieval")

    # retrieval 完成后总是进入 intent_planner（由 intent_planner 决定是否澄清）
    workflow.add_edge("retrieval", "intent_planner")

    # intent_planner -> executor, analyzer, or END (clarification)
    workflow.add_conditional_edges(
        "intent_planner",
        should_continue_to_executor,
        {
            "executor": "executor",
            "analyzer": "analyzer",
            "clarify": END
        }
    )

    # executor -> executor（循环）或 analyzer
    workflow.add_conditional_edges(
        "executor",
        should_continue_execution,
        {
            "executor": "executor",
            "analyzer": "analyzer"
        }
    )

    # analyzer -> END (无条件)
    workflow.add_edge("analyzer", END)

    # 初始化 AsyncSqliteSaver 用于状态持久化
    import os
    import aiosqlite
    os.makedirs("./data", exist_ok=True)

    # 创建数据库连接，启用 WAL 模式支持并发
    conn = aiosqlite.connect(
        "./data/checkpoints.db",
        timeout=30.0,  # 增加超时时间
        check_same_thread=False  # 允许多线程访问
    )

    # 启用 WAL 模式以支持并发读写
    async def init_wal():
        async with conn as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA busy_timeout=30000")  # 30秒超时
            await db.commit()

    import asyncio
    asyncio.create_task(init_wal())

    memory = AsyncSqliteSaver(conn)

    # 编译图（移除 interrupt_before，不再需要审批）
    graph = workflow.compile(checkpointer=memory)

    logger.info("[Graph] LangGraph workflow compiled with AsyncSqliteSaver")
    return graph
