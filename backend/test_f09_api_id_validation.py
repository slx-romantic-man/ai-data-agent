"""
F-09 测试：Planner计划结构强校验修复
验证api_id类型为字符串且与API元数据一致
"""
import asyncio
from app.agent.graph import create_graph
from app.agent.state import AgentState
from app.models.permission import PermissionContext
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def test_stock_query_api_id():
    """测试股票查询的api_id是否为字符串"""
    logger.info("=" * 60)
    logger.info("测试1：股票查询api_id类型验证")
    logger.info("=" * 60)

    permission = PermissionContext(
        user_id="test_user",
        role="employee",
        allowed_tables=[]
    )

    graph = await create_graph(permission)

    initial_state: AgentState = {
        "messages": [],
        "query": "查询苹果股票最近7个交易日的数据",
        "extracted_filters": None,
        "plan": None,
        "current_step": 0,
        "data_context": {},
        "requires_approval": False
    }

    config = {"configurable": {"thread_id": "f09_test_1"}}

    result = await graph.ainvoke(initial_state, config)

    # 检查plan中的api_id类型
    plan = result.get("plan", [])
    logger.info(f"生成的计划步骤数: {len(plan)}")

    for idx, step in enumerate(plan):
        api_id = step.get("api_id")
        logger.info(f"步骤 {idx + 1}: tool={step.get('tool')}, api_id={api_id}, api_id类型={type(api_id).__name__}")

        # 验证api_id是字符串
        if step.get("tool") == "api_fetch":
            assert isinstance(api_id, str), f"步骤{idx + 1}的api_id应为字符串，实际为{type(api_id).__name__}"
            assert api_id != "", f"步骤{idx + 1}的api_id不应为空字符串"
            logger.info(f"✓ 步骤{idx + 1} api_id类型正确: {api_id}")

    logger.info("✓ 测试1通过")
    return result


async def test_order_query_api_id():
    """测试订单查询的api_id"""
    logger.info("=" * 60)
    logger.info("测试2：订单查询api_id类型验证")
    logger.info("=" * 60)

    permission = PermissionContext(
        user_id="test_user",
        role="employee",
        allowed_tables=["orders"]
    )

    graph = await create_graph(permission)

    initial_state: AgentState = {
        "messages": [],
        "query": "查询最近7天的订单数据",
        "extracted_filters": None,
        "plan": None,
        "current_step": 0,
        "data_context": {},
        "requires_approval": False
    }

    config = {"configurable": {"thread_id": "f09_test_2"}}

    result = await graph.ainvoke(initial_state, config)

    plan = result.get("plan", [])
    logger.info(f"生成的计划步骤数: {len(plan)}")

    for idx, step in enumerate(plan):
        api_id = step.get("api_id")
        logger.info(f"步骤 {idx + 1}: tool={step.get('tool')}, api_id={api_id}, api_id类型={type(api_id).__name__}")

        if step.get("tool") == "api_fetch":
            assert isinstance(api_id, str), f"步骤{idx + 1}的api_id应为字符串"
            logger.info(f"✓ 步骤{idx + 1} api_id类型正确")

    logger.info("✓ 测试2通过")
    return result


async def main():
    """运行所有测试"""
    try:
        await test_stock_query_api_id()
        await test_order_query_api_id()
        logger.info("=" * 60)
        logger.info("所有F-09测试通过")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"测试失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
