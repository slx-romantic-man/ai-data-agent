"""
简单测试：验证 checkpointer 是否正确初始化
"""
import asyncio
from app.agent.graph import create_graph
from app.models.permission import PermissionContext
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def test_checkpointer_init():
    """测试 checkpointer 初始化"""
    permission = PermissionContext(
        user_id="test_user",
        role="admin",
        allowed_apis=["*"],
        allowed_tables=["*"]
    )

    logger.info("Creating graph with checkpointer...")
    graph = await create_graph(permission)

    logger.info(f"Graph created: {graph}")
    logger.info(f"Checkpointer: {graph.checkpointer}")

    if graph.checkpointer:
        logger.info("✅ Checkpointer initialized successfully")
    else:
        logger.error("❌ Checkpointer is None")

    return graph


if __name__ == "__main__":
    asyncio.run(test_checkpointer_init())
