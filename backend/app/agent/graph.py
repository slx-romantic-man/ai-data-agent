"""
LangGraph 工作流图定义
组装所有节点并配置边与路由逻辑
"""
from langgraph.graph import StateGraph, END
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


def should_continue_execution(state: AgentState) -> str:
    """判断 Executor 是否需要继续执行"""
    plan = state.get("plan") or []
    current_step = state.get("current_step", 0)

    if current_step < len(plan):
        return "executor"
    return "analyzer"


def should_clarify(state: AgentState) -> str:
    """判断 Intent 节点后是否需要澄清"""
    extracted_filters = state.get("extracted_filters")

    if extracted_filters is None:
        return END
    return "retrieval"


def create_graph(permission: PermissionContext):
    """
    创建 LangGraph 工作流图

    Args:
        permission: 用户权限上下文

    Returns:
        编译后的 LangGraph 图
    """

    async def retrieval_wrapper(state: AgentState) -> AgentState:
        """Retrieval 节点包装器，缓存检索结果"""
        global _retrieved_apis_cache
        result = await _retrieval_node(state)
        _retrieved_apis_cache = result.get("retrieved_apis", [])
        return state

    async def planner_wrapper(state: AgentState) -> AgentState:
        """Planner 节点包装器，传递缓存的检索结果"""
        global _retrieved_apis_cache
        return await _planner_node(state, _retrieved_apis_cache)

    async def executor_wrapper(state: AgentState) -> AgentState:
        """Executor 节点包装器"""
        return await executor_node(state, permission)

    # 创建状态图
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("intent", intent_clarification_node)
    workflow.add_node("retrieval", retrieval_wrapper)
    workflow.add_node("planner", planner_wrapper)
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
    workflow.add_edge("planner", "executor")

    workflow.add_conditional_edges(
        "executor",
        should_continue_execution,
        {
            "executor": "executor",
            "analyzer": "analyzer"
        }
    )

    workflow.add_edge("analyzer", END)

    # 编译图（设置人工审批网关）
    graph = workflow.compile(interrupt_before=["executor"])

    logger.info("[Graph] LangGraph workflow compiled successfully")
    return graph
