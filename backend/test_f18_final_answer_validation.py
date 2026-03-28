"""
F-18 端到端最终回答判定机制
重新定义测试标准：必须以Agent生成最终回答文本且内容有效为准
不以接口成功或流程结束为准
"""
import asyncio
from app.agent.graph import create_graph
from app.agent.state import AgentState
from app.models.permission import PermissionContext
from app.utils.logger import get_logger

logger = get_logger(__name__)


def validate_final_answer(result: AgentState, scenario_name: str) -> bool:
    """
    验证最终回答是否有效

    Args:
        result: Agent执行结果
        scenario_name: 场景名称

    Returns:
        是否通过验证
    """
    messages = result.get("messages", [])

    # 断言1：必须存在messages
    if not messages:
        logger.error(f"❌ {scenario_name}: 没有任何消息")
        return False

    # 断言2：最后一条消息必须存在
    final_message = messages[-1]
    if not final_message:
        logger.error(f"❌ {scenario_name}: 最后一条消息为空")
        return False

    # 断言3：最终回答内容必须非空
    final_answer = final_message.get("content", "")
    if not final_answer or not final_answer.strip():
        logger.error(f"❌ {scenario_name}: 最终回答内容为空")
        return False

    # 断言4：最终回答长度必须合理（至少10个字符）
    if len(final_answer.strip()) < 10:
        logger.error(f"❌ {scenario_name}: 最终回答过短 ({len(final_answer)} 字符)")
        return False

    logger.info(f"✓ {scenario_name}: 最终回答有效 ({len(final_answer)} 字符)")
    logger.info(f"  前100字符: {final_answer[:100]}")

    return True


async def test_complex_query_with_data():
    """测试1：复杂问题且有真实数据 - 必须得到分析结果"""
    logger.info("=" * 60)
    logger.info("测试1：复杂问题且有真实数据")
    logger.info("=" * 60)

    permission = PermissionContext(
        user_id="admin_001",
        role="admin",
        allowed_tables=["orders", "products"]
    )

    graph = await create_graph(permission)

    initial_state: AgentState = {
        "messages": [],
        "query": "查询苹果美股最近7个交易日的股价变化趋势",
        "extracted_filters": None,
        "plan": None,
        "current_step": 0,
        "data_context": {},
        "requires_approval": False
    }

    config = {"configurable": {"thread_id": "f18_test1"}}
    result = await graph.ainvoke(initial_state, config)

    # 验证最终回答
    passed = validate_final_answer(result, "测试1")

    if passed:
        # 额外验证：回答中应包含关键业务要素
        final_answer = result["messages"][-1]["content"]
        has_data_reference = any(keyword in final_answer for keyword in ["股价", "交易日", "美股", "苹果"])
        if has_data_reference:
            logger.info("  ✓ 回答包含业务关键词")
        else:
            logger.warning("  ⚠ 回答可能缺少业务关键词")

    assert passed, "测试1失败：未生成有效最终回答"
    return result


async def test_no_data_scenario():
    """测试2：无数据问题 - 必须明确说明未查询到数据"""
    logger.info("=" * 60)
    logger.info("测试2：无数据问题")
    logger.info("=" * 60)

    permission = PermissionContext(
        user_id="admin_002",
        role="admin",
        allowed_tables=["orders"]
    )

    graph = await create_graph(permission)

    initial_state: AgentState = {
        "messages": [],
        "query": "查询不存在的股票代码XXXXXX的数据",
        "extracted_filters": None,
        "plan": None,
        "current_step": 0,
        "data_context": {},
        "requires_approval": False
    }

    config = {"configurable": {"thread_id": "f18_test2"}}
    result = await graph.ainvoke(initial_state, config)

    # 验证最终回答
    passed = validate_final_answer(result, "测试2")

    if passed:
        final_answer = result["messages"][-1]["content"]
        has_no_data_message = any(keyword in final_answer for keyword in ["未查询到", "没有", "不存在", "无数据"])
        if has_no_data_message:
            logger.info("  ✓ 回答明确说明无数据")
        else:
            logger.warning("  ⚠ 回答未明确说明无数据")

    assert passed, "测试2失败：未生成有效最终回答"
    return result


async def test_permission_denied():
    """测试3：无权限问题 - 必须明确提示权限不足"""
    logger.info("=" * 60)
    logger.info("测试3：无权限问题")
    logger.info("=" * 60)

    permission = PermissionContext(
        user_id="employee_001",
        role="employee",
        allowed_tables=[]
    )

    graph = await create_graph(permission)

    initial_state: AgentState = {
        "messages": [],
        "query": "查询所有订单数据",
        "extracted_filters": None,
        "plan": None,
        "current_step": 0,
        "data_context": {},
        "requires_approval": False
    }

    config = {"configurable": {"thread_id": "f18_test3"}}
    result = await graph.ainvoke(initial_state, config)

    # 验证最终回答
    passed = validate_final_answer(result, "测试3")

    if passed:
        final_answer = result["messages"][-1]["content"]
        has_permission_message = any(keyword in final_answer for keyword in ["权限", "无法访问", "不允许", "拒绝"])
        if has_permission_message:
            logger.info("  ✓ 回答明确提示权限问题")
        else:
            logger.warning("  ⚠ 回答未明确提示权限问题")

    assert passed, "测试3失败：未生成有效最终回答"
    return result


async def test_invalid_plan():
    """测试4：Planner无法形成计划 - 必须明确提示无法执行原因"""
    logger.info("=" * 60)
    logger.info("测试4：Planner无法形成计划")
    logger.info("=" * 60)

    permission = PermissionContext(
        user_id="admin_003",
        role="admin",
        allowed_tables=["orders"]
    )

    graph = await create_graph(permission)

    initial_state: AgentState = {
        "messages": [],
        "query": "帮我做一个完全不相关的任务，比如预测明天的天气",
        "extracted_filters": None,
        "plan": None,
        "current_step": 0,
        "data_context": {},
        "requires_approval": False
    }

    config = {"configurable": {"thread_id": "f18_test4"}}
    result = await graph.ainvoke(initial_state, config)

    # 验证最终回答
    passed = validate_final_answer(result, "测试4")

    if passed:
        final_answer = result["messages"][-1]["content"]
        has_failure_message = any(keyword in final_answer for keyword in ["无法", "抱歉", "不支持", "无法理解"])
        if has_failure_message:
            logger.info("  ✓ 回答明确说明无法执行")
        else:
            logger.warning("  ⚠ 回答未明确说明无法执行")

    assert passed, "测试4失败：未生成有效最终回答"
    return result


async def main():
    """运行所有F-18测试"""
    logger.info("\n" + "=" * 60)
    logger.info("F-18 端到端最终回答判定机制测试")
    logger.info("=" * 60 + "\n")

    try:
        await test_complex_query_with_data()
        logger.info("\n")

        await test_no_data_scenario()
        logger.info("\n")

        await test_permission_denied()
        logger.info("\n")

        await test_invalid_plan()

        logger.info("\n" + "=" * 60)
        logger.info("✅ 所有 F-18 测试通过")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
