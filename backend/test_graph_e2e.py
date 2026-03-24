"""
端到端测试：验证完整的图执行流程（包括 Executor 和 Analyzer）
"""
import asyncio
from app.agent.graph import create_graph
from app.agent.state import AgentState
from app.models.permission import PermissionContext
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def test_e2e_with_execution():
    """端到端测试：完整执行流程"""
    permission = PermissionContext(
        user_id="test_user",
        role="admin",
        allowed_apis=["*"],
        allowed_tables=["*"]
    )

    graph = await create_graph(permission)

    initial_state: AgentState = {
        "messages": [],
        "query": "查询2024年1月华东地区的销售额和订单量，按省份统计",
        "extracted_filters": None,
        "plan": None,
        "current_step": 0,
        "data_context": {}
    }

    logger.info("=" * 60)
    logger.info("E2E Test: Full execution with Executor and Analyzer")
    logger.info("=" * 60)

    try:
        # 第一次调用：执行到 interrupt_before Executor
        config = {"configurable": {"thread_id": "test_thread_1"}}
        result = await graph.ainvoke(initial_state, config)

        logger.info("\nPhase 1: Reached interrupt point")
        logger.info(f"  Plan generated: {len(result.get('plan', []))} steps")

        # 第二次调用：继续执行（模拟审批通过）
        result = await graph.ainvoke(result, config)

        logger.info("\nPhase 2: Execution completed")
        logger.info(f"  Steps executed: {result.get('current_step')}")
        logger.info(f"  Data collected: {len(result.get('data_context', {}))}")
        logger.info(f"  Messages: {len(result.get('messages', []))}")

        # 验证结果
        assert result.get('current_step', 0) > 0, "No steps executed"
        assert len(result.get('data_context', {})) > 0, "No data collected"
        assert len(result.get('messages', [])) > 0, "No analysis generated"

        logger.info("\nTest PASSED: Full E2E flow completed successfully")
        return result

    except Exception as e:
        logger.error(f"Test FAILED: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(test_e2e_with_execution())
