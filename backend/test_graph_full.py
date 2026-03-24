"""
测试完整的 LangGraph 工作流（条件完备场景）
"""
import asyncio
from app.agent.graph import create_graph
from app.agent.state import AgentState
from app.models.permission import PermissionContext
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def test_full_flow():
    """测试完整流程：条件完备的查询"""
    permission = PermissionContext(
        user_id="test_user",
        role="admin",
        allowed_apis=["*"],
        allowed_tables=["*"]
    )

    graph = create_graph(permission)

    # 使用条件完备的查询
    initial_state: AgentState = {
        "messages": [],
        "query": "查询2024年1月华东地区的销售数据，包括销售额和订单量",
        "extracted_filters": None,
        "plan": None,
        "current_step": 0,
        "data_context": {}
    }

    logger.info("=" * 60)
    logger.info("Testing full graph flow with complete query")
    logger.info("=" * 60)

    try:
        result = await graph.ainvoke(initial_state)

        logger.info("\n" + "=" * 60)
        logger.info("Graph execution completed successfully")
        logger.info("=" * 60)

        logger.info(f"\nFinal state summary:")
        logger.info(f"  Messages: {len(result.get('messages', []))}")
        logger.info(f"  Has filters: {result.get('extracted_filters') is not None}")
        plan = result.get('plan') or []
        logger.info(f"  Plan steps: {len(plan)}")
        logger.info(f"  Executed steps: {result.get('current_step')}")
        logger.info(f"  Data collected: {len(result.get('data_context', {}))}")

        if plan:
            logger.info(f"\nExecution plan:")
            for i, step in enumerate(plan):
                logger.info(f"  Step {i+1}: {step.get('description')}")

        logger.info("\n✅ Full flow test PASSED")
        return result

    except Exception as e:
        logger.error(f"❌ Full flow test FAILED: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(test_full_flow())
