"""
F-13 API全量复杂问题覆盖测试集 - 简化版
快速验证测试框架
"""
import asyncio
from app.agent.graph import create_graph
from app.agent.state import AgentState
from app.models.permission import PermissionContext
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def test_single_api():
    """测试单个API"""
    logger.info("=" * 60)
    logger.info("F-13 快速验证测试")
    logger.info("=" * 60)

    permission = PermissionContext(
        user_id="admin",
        role="admin",
        allowed_tables=["orders", "products"]
    )

    graph = await create_graph(permission)

    initial_state: AgentState = {
        "messages": [],
        "query": "查询苹果公司最近一周的股价走势",
        "extracted_filters": None,
        "plan": None,
        "current_step": 0,
        "data_context": {},
        "requires_approval": False
    }

    config = {"configurable": {"thread_id": "f13_quick_test"}}
    result = await graph.ainvoke(initial_state, config)

    messages = result.get("messages", [])
    if messages:
        final_answer = messages[-1].get("content", "")
        logger.info(f"✓ 测试通过，获得最终回答 ({len(final_answer)} 字符)")
        logger.info(f"回答: {final_answer[:200]}...")
        return True
    else:
        logger.error("❌ 测试失败，未获得最终回答")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_single_api())
    if result:
        print("\n✅ F-13 框架验证通过")
    else:
        print("\n❌ F-13 框架验证失败")
