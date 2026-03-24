"""
简化测试：直接测试 Retrieval -> Planner -> Executor -> Analyzer 流程
跳过 Intent 节点，手动设置 extracted_filters
"""
import asyncio
from langgraph.graph import StateGraph, END
from app.agent.state import AgentState
from app.agent.nodes.retrieval_node import retrieval_node as _retrieval_node
from app.agent.nodes.planner_node import planner_node as _planner_node
from app.agent.nodes.executor_node import executor_node
from app.agent.nodes.analyzer_node import analyzer_node
from app.models.permission import PermissionContext
from app.utils.logger import get_logger

logger = get_logger(__name__)

_retrieved_apis_cache = []


async def test_simplified_flow():
    """简化测试：跳过 Intent，直接测试核心流程"""
    permission = PermissionContext(
        user_id="test_user",
        role="admin",
        allowed_apis=["*"],
        allowed_tables=["*"]
    )

    async def retrieval_wrapper(state: AgentState) -> AgentState:
        global _retrieved_apis_cache
        result = await _retrieval_node(state)
        _retrieved_apis_cache = result.get("retrieved_apis", [])
        return state

    async def planner_wrapper(state: AgentState) -> AgentState:
        global _retrieved_apis_cache
        return await _planner_node(state, _retrieved_apis_cache)

    def should_continue(state: AgentState) -> str:
        plan = state.get("plan") or []
        current_step = state.get("current_step", 0)
        return "executor" if current_step < len(plan) else "analyzer"

    async def executor_wrapper(state: AgentState) -> AgentState:
        return await executor_node(state, permission)

    # 构建简化图
    workflow = StateGraph(AgentState)
    workflow.add_node("retrieval", retrieval_wrapper)
    workflow.add_node("planner", planner_wrapper)
    workflow.add_node("executor", executor_wrapper)
    workflow.add_node("analyzer", analyzer_node)

    workflow.set_entry_point("retrieval")
    workflow.add_edge("retrieval", "planner")
    workflow.add_edge("planner", "executor")
    workflow.add_conditional_edges("executor", should_continue, {
        "executor": "executor",
        "analyzer": "analyzer"
    })
    workflow.add_edge("analyzer", END)

    graph = workflow.compile()

    # 手动设置 extracted_filters
    initial_state: AgentState = {
        "messages": [],
        "query": "查询2024年1月华东地区销售数据",
        "extracted_filters": {
            "intent_type": "api_query",
            "entities": {"location": "华东地区"},
            "metrics": ["销售额"],
            "dimensions": ["地区"],
            "confidence": 0.9
        },
        "plan": None,
        "current_step": 0,
        "data_context": {}
    }

    logger.info("=" * 60)
    logger.info("Simplified Flow Test")
    logger.info("=" * 60)

    try:
        result = await graph.ainvoke(initial_state)

        logger.info("\nTest Results:")
        logger.info(f"  Plan steps: {len(result.get('plan', []))}")
        logger.info(f"  Executed: {result.get('current_step')}")
        logger.info(f"  Data: {len(result.get('data_context', {}))}")
        logger.info(f"  Messages: {len(result.get('messages', []))}")

        logger.info("\nTest PASSED")
        return result

    except Exception as e:
        logger.error(f"Test FAILED: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(test_simplified_flow())
