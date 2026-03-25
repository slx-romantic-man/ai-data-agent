"""
F-11 端到端测试：简单查询场景
测试目标：验证系统能够正确处理简单的 SQL 查询并返回结果
"""
import asyncio
from app.agent.graph import create_graph
from app.agent.state import AgentState
from app.models.permission import PermissionContext
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def test_simple_query():
    """测试简单查询：今天有多少用户注册？"""
    permission = PermissionContext(
        user_id="test_user",
        role="admin",
        allowed_apis=["*"],
        allowed_tables=["*"]
    )

    graph = await create_graph(permission)

    initial_state: AgentState = {
        "messages": [],
        "query": "今天有多少用户注册？",
        "extracted_filters": None,
        "plan": None,
        "current_step": 0,
        "data_context": {}
    }

    logger.info("=" * 60)
    logger.info("F-11 Test: Simple Query Scenario")
    logger.info("Query: 今天有多少用户注册？")
    logger.info("=" * 60)

    try:
        config = {"configurable": {"thread_id": "f11_test_thread"}}

        # 第一次调用：执行到 interrupt 点（如果有）
        result = await graph.ainvoke(initial_state, config)

        logger.info("\n[Phase 1] After first invoke:")
        logger.info(f"  Plan: {result.get('plan')}")
        logger.info(f"  Current step: {result.get('current_step')}")

        # 如果有 plan，继续执行
        if result.get('plan'):
            result = await graph.ainvoke(result, config)
            logger.info("\n[Phase 2] After second invoke (execution):")
            logger.info(f"  Steps executed: {result.get('current_step')}")
            logger.info(f"  Data context keys: {list(result.get('data_context', {}).keys())}")

        # 验证结果
        messages = result.get('messages', [])
        logger.info(f"\n[Result] Total messages: {len(messages)}")

        if messages:
            last_message = messages[-1]
            logger.info(f"  Last message type: {type(last_message)}")
            logger.info(f"  Last message content preview: {str(last_message)[:200]}...")

        # 检查是否包含 SQL 工具调用
        data_context = result.get('data_context', {})
        has_sql_result = any('sql' in key.lower() for key in data_context.keys())

        logger.info(f"\n[Validation]")
        logger.info(f"  ✓ Has plan: {result.get('plan') is not None}")
        logger.info(f"  ✓ Has SQL result: {has_sql_result}")
        logger.info(f"  ✓ Has analysis: {len(messages) > 0}")

        assert result.get('plan') is not None, "No plan generated"
        assert has_sql_result or len(data_context) > 0, "No data collected"
        assert len(messages) > 0, "No analysis generated"

        logger.info("\n✅ Test PASSED: Simple query scenario completed successfully")
        return result

    except Exception as e:
        logger.error(f"\n❌ Test FAILED: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(test_simple_query())
