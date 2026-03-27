"""
F-04 简化测试：直接测试Planner和Analyzer的空计划处理逻辑
"""
import asyncio
from app.agent.nodes.planner_node import _create_fallback_plan
from app.agent.nodes.analyzer_node import analyzer_node
from app.agent.state import AgentState
from app.utils.logger import get_logger

logger = get_logger(__name__)


def test_fallback_plan_empty():
    """测试1：当没有API时，fallback plan返回空列表"""
    logger.info("=" * 60)
    logger.info("测试1：Fallback plan with no APIs")
    logger.info("=" * 60)

    result = _create_fallback_plan("查询火星房价", [])

    assert result == [], f"Expected empty list, got {result}"
    logger.info("✅ 验证通过：无API时返回空计划")


async def test_analyzer_handles_empty_plan():
    """测试2：Analyzer正确处理空计划"""
    logger.info("\n" + "=" * 60)
    logger.info("测试2：Analyzer handles empty plan")
    logger.info("=" * 60)

    state: AgentState = {
        "messages": [],
        "query": "查询火星房价",
        "extracted_filters": {},
        "plan": [],
        "current_step": 0,
        "data_context": {}
    }

    result = await analyzer_node(state)

    messages = result.get("messages", [])
    assert len(messages) > 0, "Expected at least one message"

    last_message = messages[-1]
    content = last_message.get("content", "")

    assert "抱歉" in content or "无法执行" in content, \
        f"Expected error message, got: {content}"
    logger.info(f"✅ 验证通过：Analyzer返回错误信息")
    logger.info(f"   消息内容: {content[:100]}...")


async def test_analyzer_handles_error_field():
    """测试3：Analyzer正确处理error字段"""
    logger.info("\n" + "=" * 60)
    logger.info("测试3：Analyzer handles error field")
    logger.info("=" * 60)

    state: AgentState = {
        "messages": [],
        "query": "查询股票数据",
        "extracted_filters": {},
        "plan": [],
        "current_step": 0,
        "data_context": {},
        "error": "你没有该 API 的使用权限，请联系管理员授权。"
    }

    result = await analyzer_node(state)

    messages = result.get("messages", [])
    assert len(messages) > 0, "Expected at least one message"

    last_message = messages[-1]
    content = last_message.get("content", "")

    assert "权限" in content, f"Expected permission error, got: {content}"
    logger.info(f"✅ 验证通过：Analyzer使用error字段")
    logger.info(f"   消息内容: {content[:100]}...")


async def main():
    logger.info("\n" + "🚀" * 30)
    logger.info("F-04 简化测试开始")
    logger.info("🚀" * 30 + "\n")

    # 测试1：Fallback plan
    test_fallback_plan_empty()

    # 测试2：Analyzer处理空计划
    await test_analyzer_handles_empty_plan()

    # 测试3：Analyzer处理error字段
    await test_analyzer_handles_error_field()

    logger.info("\n" + "🎉" * 30)
    logger.info("F-04 所有测试通过！")
    logger.info("🎉" * 30)


if __name__ == "__main__":
    asyncio.run(main())
