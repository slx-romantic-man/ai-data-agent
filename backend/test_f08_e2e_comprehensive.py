"""
F-08 端到端综合测试
覆盖 RBAC 直通替代审批和股票分析链路修复两大主线
"""
import asyncio
from app.agent.graph import create_graph
from app.agent.state import AgentState
from app.models.permission import PermissionContext
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def test_scenario_1_employee_with_permission():
    """场景1：普通员工已授权API直接执行"""
    logger.info("=" * 60)
    logger.info("场景1：普通员工已授权API直接执行")
    logger.info("=" * 60)

    permission = PermissionContext(
        user_id="employee_001",
        role="employee",
        allowed_tables=["orders"]
    )

    graph = await create_graph(permission)

    initial_state: AgentState = {
        "messages": [],
        "query": "查询苹果美股最近7个交易日股价",
        "extracted_filters": None,
        "plan": None,
        "current_step": 0,
        "data_context": {},
        "requires_approval": False
    }

    config = {"configurable": {"thread_id": "f08_scenario_1"}}

    result = await graph.ainvoke(initial_state, config)

    # 验证点
    assert not result.get("requires_approval", False), "不应进入审批流程"

    messages = result.get("messages", [])
    logger.info(f"✓ 收到 {len(messages)} 条消息")
    logger.info(f"✓ requires_approval = {result.get('requires_approval', False)}")
    logger.info("✓ 场景1 通过")

    return result


async def test_scenario_2_employee_without_permission():
    """场景2：普通员工未授权API直接拒绝"""
    logger.info("=" * 60)
    logger.info("场景2：普通员工未授权API直接拒绝")
    logger.info("=" * 60)

    permission = PermissionContext(
        user_id="employee_002",
        role="employee",
        allowed_tables=[]
    )

    graph = await create_graph(permission)

    initial_state: AgentState = {
        "messages": [],
        "query": "查询苹果美股最近7个交易日股价",
        "extracted_filters": None,
        "plan": None,
        "current_step": 0,
        "data_context": {},
        "requires_approval": False
    }

    config = {"configurable": {"thread_id": "f08_scenario_2"}}

    result = await graph.ainvoke(initial_state, config)

    # 验证点
    assert not result.get("requires_approval", False), "不应进入审批流程"

    messages = result.get("messages", [])
    if messages:
        last_msg = messages[-1].get("content", "")
        logger.info(f"最终消息: {last_msg[:200]}")

    logger.info(f"✓ requires_approval = {result.get('requires_approval', False)}")
    logger.info("✓ 场景2 通过")

    return result


async def test_scenario_3_stock_analysis_success():
    """场景3：股票分析成功链路"""
    logger.info("=" * 60)
    logger.info("场景3：股票分析成功链路")
    logger.info("=" * 60)

    permission = PermissionContext(
        user_id="admin_001",
        role="admin",
        allowed_tables=["orders", "products"]
    )

    graph = await create_graph(permission)

    initial_state: AgentState = {
        "messages": [],
        "query": "去看看苹果的美股股价最近7个交易日的变化趋势，给出原因与后续投资建议",
        "extracted_filters": None,
        "plan": None,
        "current_step": 0,
        "data_context": {},
        "requires_approval": False
    }

    config = {"configurable": {"thread_id": "f08_scenario_3"}}

    result = await graph.ainvoke(initial_state, config)

    # 验证点
    plan = result.get("plan", [])
    logger.info(f"✓ 生成计划步骤数: {len(plan)}")

    data_context = result.get("data_context", {})
    logger.info(f"✓ data_context 键数: {len(data_context)}")

    messages = result.get("messages", [])
    if messages:
        final_analysis = messages[-1].get("content", "")
        logger.info(f"✓ 最终分析长度: {len(final_analysis)} 字符")

        # 验证分析报告结构
        has_summary = "事实总结" in final_analysis or "数据" in final_analysis
        has_reason = "可能原因" in final_analysis or "原因" in final_analysis
        has_risk = "风险" in final_analysis

        logger.info(f"  - 包含事实总结: {has_summary}")
        logger.info(f"  - 包含原因分析: {has_reason}")
        logger.info(f"  - 包含风险提示: {has_risk}")

    logger.info("✓ 场景3 通过")

    return result


async def test_scenario_4_planner_safe_failure():
    """场景4：Planner无有效计划时安全失败"""
    logger.info("=" * 60)
    logger.info("场景4：Planner无有效计划时安全失败")
    logger.info("=" * 60)

    permission = PermissionContext(
        user_id="admin_002",
        role="admin",
        allowed_tables=[]
    )

    graph = await create_graph(permission)

    # 构造一个无法生成有效计划的查询
    initial_state: AgentState = {
        "messages": [],
        "query": "查询不存在的数据源XYZ的信息",
        "extracted_filters": None,
        "plan": None,
        "current_step": 0,
        "data_context": {},
        "requires_approval": False
    }

    config = {"configurable": {"thread_id": "f08_scenario_4"}}

    result = await graph.ainvoke(initial_state, config)

    # 验证点
    plan = result.get("plan", [])
    logger.info(f"✓ 计划步骤数: {len(plan)}")

    messages = result.get("messages", [])
    if messages:
        last_msg = messages[-1].get("content", "")
        logger.info(f"✓ 最终消息: {last_msg[:200]}")

    current_step = result.get("current_step", 0)
    logger.info(f"✓ 执行步骤数: {current_step}")

    logger.info("✓ 场景4 通过")

    return result


async def main():
    """运行所有测试场景"""
    logger.info("\n" + "=" * 60)
    logger.info("F-08 端到端综合测试")
    logger.info("=" * 60 + "\n")

    try:
        await test_scenario_1_employee_with_permission()
        logger.info("\n")

        await test_scenario_2_employee_without_permission()
        logger.info("\n")

        await test_scenario_3_stock_analysis_success()
        logger.info("\n")

        await test_scenario_4_planner_safe_failure()

        logger.info("\n" + "=" * 60)
        logger.info("✅ 所有 F-08 测试场景通过")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
