"""
F-04 测试：建立Planner输出校验和安全失败机制
验证空计划不会触发伪执行，且用户收到明确的失败原因
"""
import asyncio
from app.agent.graph import create_graph
from app.agent.state import AgentState
from app.models.permission import PermissionContext
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def test_empty_plan_safe_failure():
    """测试场景：构造无法生成有效计划的查询"""

    # 模拟普通员工权限
    permission = PermissionContext(
        user_id="2",
        role="employee",
        permissions=[]
    )

    # 创建工作流
    graph = await create_graph(permission)

    # 构造一个无法生成有效计划的查询（没有匹配的API）
    initial_state: AgentState = {
        "messages": [],
        "query": "查询火星上的房价数据",  # 明显无法匹配任何API
        "extracted_filters": None,
        "plan": None,
        "current_step": 0,
        "data_context": {}
    }

    config = {"configurable": {"thread_id": "test_f04_empty_plan"}}

    logger.info("=" * 60)
    logger.info("F-04 测试开始：空计划安全失败机制")
    logger.info("=" * 60)

    final_state = None
    executor_executed = False

    async for event in graph.astream(initial_state, config, stream_mode="updates"):
        for node_name, node_output in event.items():
            logger.info(f"\n[节点执行] {node_name}")

            if node_name == "planner":
                plan = node_output.get("plan", [])
                error = node_output.get("error")
                logger.info(f"  - Plan steps: {len(plan)}")
                logger.info(f"  - Error: {error}")

            if node_name == "executor":
                executor_executed = True
                logger.info("  ⚠️  Executor 被执行了！")

            if node_name == "analyzer":
                messages = node_output.get("messages", [])
                if messages:
                    final_msg = messages[-1]
                    logger.info(f"  - Final message: {final_msg.get('content', '')[:200]}")

            final_state = node_output

    logger.info("\n" + "=" * 60)
    logger.info("F-04 测试结果验证")
    logger.info("=" * 60)

    # 验证点1：Planner返回空计划
    plan = final_state.get("plan", [])
    assert len(plan) == 0, f"❌ 预期空计划，实际有 {len(plan)} 步"
    logger.info("✅ 验证通过：Planner返回空计划")

    # 验证点2：Executor未执行
    assert not executor_executed, "❌ Executor不应该被执行"
    logger.info("✅ 验证通过：Executor未执行任何步骤")

    # 验证点3：存在错误信息
    error = final_state.get("error")
    messages = final_state.get("messages", [])
    has_error_message = any("无法执行" in msg.get("content", "") or "抱歉" in msg.get("content", "") for msg in messages)

    assert error or has_error_message, "❌ 应该有明确的失败原因说明"
    logger.info(f"✅ 验证通过：存在失败原因说明")

    # 验证点4：data_context为空（没有执行任何工具）
    data_context = final_state.get("data_context", {})
    assert len(data_context) == 0, f"❌ data_context应该为空，实际有 {len(data_context)} 项"
    logger.info("✅ 验证通过：data_context为空，未执行任何工具")

    logger.info("\n" + "=" * 60)
    logger.info("🎉 F-04 所有验证点通过！")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_empty_plan_safe_failure())
