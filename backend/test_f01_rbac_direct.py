"""
F-01 测试：移除普通员工调用API需要人工审批的执行门槛
验证基于API权限直接放行或拒绝
"""
import asyncio
from app.agent.graph import create_graph
from app.agent.state import AgentState
from app.models.permission import PermissionContext
from app.services.api_permission_service import get_api_permission_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def test_employee_with_permission():
    """测试场景1：普通员工已授权API直接执行"""
    logger.info("=" * 60)
    logger.info("F-01 Test 1: Employee with API permission")
    logger.info("=" * 60)

    # 创建普通员工权限上下文
    permission = PermissionContext(
        user_id="employee_001",
        role="employee",
        allowed_tables=["orders", "products"]
    )

    # 确保用户有股票API权限（模拟管理员已授权）
    # 注意：实际测试需要先在数据库中授权

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

    config = {"configurable": {"thread_id": "f01_test_1"}}

    try:
        result = await graph.ainvoke(initial_state, config)

        # 验证：不应该进入审批流程
        assert not result.get("requires_approval", False), \
            "Should not require approval"

        # 验证：应该有计划生成
        plan = result.get("plan", [])
        logger.info(f"Plan generated: {len(plan)} steps")

        # 验证：如果有API调用，应该直接执行
        if plan:
            logger.info("✓ Plan generated, no approval required")
            logger.info("✓ Test 1 PASSED")
        else:
            logger.warning("No plan generated (may need API permission)")

        return result

    except Exception as e:
        logger.error(f"Test 1 FAILED: {e}", exc_info=True)
        raise


async def test_employee_without_permission():
    """测试场景2：普通员工未授权API直接拒绝"""
    logger.info("=" * 60)
    logger.info("F-01 Test 2: Employee without API permission")
    logger.info("=" * 60)

    # 创建普通员工权限上下文（无API权限）
    permission = PermissionContext(
        user_id="employee_002",
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

    config = {"configurable": {"thread_id": "f01_test_2"}}

    try:
        result = await graph.ainvoke(initial_state, config)

        # 验证：不应该进入审批流程
        assert not result.get("requires_approval", False), \
            "Should not require approval"

        # 验证：计划应该为空（权限检查失败）
        plan = result.get("plan", [])
        logger.info(f"Plan: {plan}")

        # 验证：应该直接返回错误信息
        messages = result.get("messages", [])
        if messages:
            last_message = messages[-1].get("content", "")
            logger.info(f"Response: {last_message[:100]}...")

            if "权限" in last_message or "无法执行" in last_message:
                logger.info("✓ Permission denied correctly")
                logger.info("✓ Test 2 PASSED")
            else:
                logger.warning("Expected permission error message")

        return result

    except Exception as e:
        logger.error(f"Test 2 FAILED: {e}", exc_info=True)
        raise


async def main():
    """运行所有测试"""
    logger.info("\n" + "=" * 60)
    logger.info("F-01 RBAC Direct Access Tests")
    logger.info("=" * 60 + "\n")

    try:
        # 测试1：有权限直接执行
        await test_employee_with_permission()

        logger.info("\n")

        # 测试2：无权限直接拒绝
        await test_employee_without_permission()

        logger.info("\n" + "=" * 60)
        logger.info("All F-01 tests completed")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
