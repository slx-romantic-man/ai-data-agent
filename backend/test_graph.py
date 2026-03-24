"""
测试 LangGraph 工作流图
验证从用户查询到最终分析的完整流程
"""
import asyncio
from app.agent.graph import create_graph
from app.agent.state import AgentState
from app.models.permission import PermissionContext
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def test_graph_flow():
    """测试完整的图流程"""
    # 创建权限上下文
    permission = PermissionContext(
        user_id="test_user",
        role="admin",
        allowed_apis=["*"],
        allowed_tables=["*"]
    )

    # 创建图
    graph = await create_graph(permission)

    # 初始化状态
    initial_state: AgentState = {
        "messages": [],
        "query": "查询华东地区的销售数据",
        "extracted_filters": None,
        "plan": None,
        "current_step": 0,
        "data_context": {}
    }

    logger.info("=" * 60)
    logger.info("Starting graph execution test")
    logger.info("=" * 60)

    # 执行图
    try:
        result = await graph.ainvoke(initial_state)

        logger.info("\n" + "=" * 60)
        logger.info("Graph execution completed")
        logger.info("=" * 60)

        # 打印结果
        logger.info(f"\nFinal state:")
        logger.info(f"  - Messages count: {len(result.get('messages', []))}")
        logger.info(f"  - Extracted filters: {result.get('extracted_filters') is not None}")
        plan = result.get('plan') or []
        logger.info(f"  - Plan steps: {len(plan)}")
        logger.info(f"  - Current step: {result.get('current_step')}")
        logger.info(f"  - Data context keys: {list(result.get('data_context', {}).keys())}")

        # 打印消息
        for i, msg in enumerate(result.get('messages', [])):
            logger.info(f"\nMessage {i + 1}:")
            logger.info(f"  Role: {msg.get('role')}")
            logger.info(f"  Type: {msg.get('type', 'N/A')}")
            logger.info(f"  Content: {msg.get('content', '')[:200]}...")

        return result

    except Exception as e:
        logger.error(f"Graph execution failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(test_graph_flow())
