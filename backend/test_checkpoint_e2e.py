"""
端到端测试：验证状态持久化功能
测试多轮对话中 data_context 的保存和恢复
"""
import asyncio
from app.agent.graph import create_graph
from app.agent.state import AgentState
from app.models.permission import PermissionContext
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def test_checkpoint_persistence():
    """测试状态持久化"""
    permission = PermissionContext(
        user_id="test_user",
        role="admin",
        allowed_apis=["*"],
        allowed_tables=["*"]
    )

    graph = await create_graph(permission)
    thread_id = "test_checkpoint_thread_001"
    config = {"configurable": {"thread_id": thread_id}}

    logger.info("=" * 60)
    logger.info("Test: Checkpoint Persistence")
    logger.info("=" * 60)

    # 第一轮：初始化状态
    logger.info("\n[Round 1] Initialize state with query")
    initial_state: AgentState = {
        "messages": [],
        "query": "查询华东地区销售数据",
        "extracted_filters": {"region": "华东"},
        "plan": [
            {"step": 1, "tool": "api_fetch", "description": "获取销售数据"}
        ],
        "current_step": 0,
        "data_context": {"test_key": "test_value"}
    }

    result1 = await graph.ainvoke(initial_state, config)
    logger.info(f"Round 1 completed")
    logger.info(f"  data_context: {result1.get('data_context')}")

    # 第二轮：从 checkpoint 恢复
    logger.info("\n[Round 2] Resume from checkpoint")
    result2 = await graph.ainvoke(None, config)
    logger.info(f"Round 2 completed")
    logger.info(f"  data_context: {result2.get('data_context')}")

    # 验证
    if result2.get('data_context'):
        logger.info("\nPASS: data_context was restored from checkpoint")
        return True
    else:
        logger.error("\nFAIL: data_context was not restored")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_checkpoint_persistence())
    exit(0 if result else 1)
