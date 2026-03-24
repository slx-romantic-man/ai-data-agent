"""
测试 LangGraph 状态持久化功能
验证多轮对话能够正确保存和恢复 AgentState
"""
import asyncio
from app.agent.graph import create_graph
from app.agent.state import AgentState
from app.models.permission import PermissionContext
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def test_state_persistence():
    """测试状态持久化：多轮对话场景"""
    permission = PermissionContext(
        user_id="test_user",
        role="admin",
        allowed_apis=["*"],
        allowed_tables=["*"]
    )

    graph = await create_graph(permission)
    thread_id = "test_persistence_thread"
    config = {"configurable": {"thread_id": thread_id}}

    logger.info("=" * 60)
    logger.info("Test: State Persistence with Multi-turn Conversation")
    logger.info("=" * 60)

    # 第一轮对话
    logger.info("\n[Round 1] Initial query")
    initial_state: AgentState = {
        "messages": [],
        "query": "查询华东地区的销售数据",
        "extracted_filters": None,
        "plan": None,
        "current_step": 0,
        "data_context": {}
    }

    result1 = await graph.ainvoke(initial_state, config)
    logger.info(f"  Plan generated: {len(result1.get('plan', []))} steps")
    logger.info(f"  Data context keys: {list(result1.get('data_context', {}).keys())}")

    # 第二轮对话：从 checkpoint 恢复
    logger.info("\n[Round 2] Resume from checkpoint")
    result2 = await graph.ainvoke(None, config)
    logger.info(f"  Current step: {result2.get('current_step')}")
    logger.info(f"  Data context preserved: {len(result2.get('data_context', {}))}")

    # 验证 data_context 被正确恢复
    assert result2.get('data_context') is not None, "data_context not restored"
    assert len(result2.get('data_context', {})) > 0, "data_context is empty"

    logger.info("\n✅ State persistence test PASSED")
    logger.info(f"  - State saved to thread_id: {thread_id}")
    logger.info(f"  - data_context successfully restored in round 2")
    return result2


if __name__ == "__main__":
    asyncio.run(test_state_persistence())
