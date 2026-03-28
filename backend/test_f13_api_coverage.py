"""
F-13 API全量复杂问题覆盖测试集
为系统当前已接入的全部API建立复杂自然语言问题测试集
每个API至少1-3条真实复杂问题
"""
import asyncio
from typing import Dict, List
from app.agent.graph import create_graph
from app.agent.state import AgentState
from app.models.permission import PermissionContext
from app.utils.logger import get_logger

logger = get_logger(__name__)


# API测试问题映射表
API_TEST_QUESTIONS = {
    "alpha_vantage_stock": [
        "查询苹果公司最近一周的股价走势，并分析涨跌幅度",
        "帮我看看特斯拉股票最近5个交易日的收盘价变化趋势",
        "IBM的股票在过去7天内表现如何？有没有明显的波动？"
    ],
    "weather_api": [
        "北京今天的天气怎么样？温度多少度？",
        "上海未来三天会下雨吗？需要带伞吗？",
        "深圳这周末适合户外活动吗？天气条件如何？"
    ],
    "weather_api_v2": [
        "广州明天的气温预计是多少？会不会很热？",
        "成都这几天的天气变化趋势是怎样的？",
        "杭州下周的天气预报显示会有什么变化？"
    ],
    "inventory_api_v5": [
        "仓库里还有多少台iPhone 14 Pro？库存充足吗？",
        "帮我查一下MacBook Air的当前库存数量和位置",
        "AirPods Pro 2代的库存状态如何？哪个仓库有货？"
    ],
    "chanjet_ip_loc": [
        "IP地址8.8.8.8是哪个国家的？具体位置在哪里？",
        "帮我查询114.114.114.114这个IP的地理位置信息",
        "1.1.1.1这个IP地址属于哪个地区？运营商是谁？"
    ]
}


def validate_final_answer(result: AgentState, api_id: str, question: str) -> bool:
    """
    验证最终回答是否有效

    Args:
        result: Agent执行结果
        api_id: API标识
        question: 测试问题

    Returns:
        是否通过验证
    """
    messages = result.get("messages", [])

    if not messages:
        logger.error(f"❌ [{api_id}] 没有任何消息")
        return False

    final_message = messages[-1]
    if not final_message:
        logger.error(f"❌ [{api_id}] 最后一条消息为空")
        return False

    final_answer = final_message.get("content", "")
    if not final_answer or not final_answer.strip():
        logger.error(f"❌ [{api_id}] 最终回答内容为空")
        return False

    if len(final_answer.strip()) < 10:
        logger.error(f"❌ [{api_id}] 最终回答过短 ({len(final_answer)} 字符)")
        return False

    logger.info(f"✓ [{api_id}] 最终回答有效 ({len(final_answer)} 字符)")
    logger.info(f"  问题: {question[:50]}...")
    logger.info(f"  回答前100字符: {final_answer[:100]}")

    return True


async def test_api_question(api_id: str, question: str, test_index: int) -> Dict:
    """
    测试单个API的单个问题

    Args:
        api_id: API标识
        question: 测试问题
        test_index: 测试序号

    Returns:
        测试结果字典
    """
    logger.info("=" * 60)
    logger.info(f"测试 [{api_id}] 问题 {test_index}")
    logger.info(f"问题: {question}")
    logger.info("=" * 60)

    permission = PermissionContext(
        user_id="admin",
        role="admin",
        allowed_tables=["orders", "products", "inventory"]
    )

    graph = await create_graph(permission)

    initial_state: AgentState = {
        "messages": [],
        "query": question,
        "extracted_filters": None,
        "plan": None,
        "current_step": 0,
        "data_context": {},
        "requires_approval": False
    }

    config = {"configurable": {"thread_id": f"f13_{api_id}_{test_index}"}}

    try:
        result = await graph.ainvoke(initial_state, config)
        passed = validate_final_answer(result, api_id, question)

        return {
            "api_id": api_id,
            "question": question,
            "passed": passed,
            "final_answer": result["messages"][-1]["content"] if result.get("messages") else None,
            "error": None
        }
    except Exception as e:
        logger.error(f"❌ [{api_id}] 测试异常: {e}", exc_info=True)
        return {
            "api_id": api_id,
            "question": question,
            "passed": False,
            "final_answer": None,
            "error": str(e)
        }


async def test_all_apis():
    """
    测试所有API的所有问题

    Returns:
        测试结果汇总
    """
    logger.info("\n" + "=" * 60)
    logger.info("F-13 API全量复杂问题覆盖测试")
    logger.info("=" * 60 + "\n")

    all_results = []

    for api_id, questions in API_TEST_QUESTIONS.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"开始测试 API: {api_id}")
        logger.info(f"测试问题数: {len(questions)}")
        logger.info(f"{'='*60}\n")

        for idx, question in enumerate(questions, 1):
            result = await test_api_question(api_id, question, idx)
            all_results.append(result)
            logger.info("")

    return all_results


def generate_report(results: List[Dict]):
    """
    生成测试报告

    Args:
        results: 所有测试结果
    """
    logger.info("\n" + "=" * 60)
    logger.info("F-13 测试报告")
    logger.info("=" * 60 + "\n")

    # 按API分组统计
    api_stats = {}
    for result in results:
        api_id = result["api_id"]
        if api_id not in api_stats:
            api_stats[api_id] = {"total": 0, "passed": 0, "failed": 0}

        api_stats[api_id]["total"] += 1
        if result["passed"]:
            api_stats[api_id]["passed"] += 1
        else:
            api_stats[api_id]["failed"] += 1

    # 输出API维度报告
    logger.info("API维度测试结果:")
    logger.info("-" * 60)

    all_passed = True
    for api_id, stats in api_stats.items():
        status = "✅ PASS" if stats["failed"] == 0 else "❌ FAIL"
        logger.info(f"{status} | {api_id:25s} | {stats['passed']}/{stats['total']} 通过")

        if stats["failed"] > 0:
            all_passed = False
            # 输出失败的问题
            for result in results:
                if result["api_id"] == api_id and not result["passed"]:
                    logger.error(f"  ❌ 失败问题: {result['question'][:60]}...")
                    if result["error"]:
                        logger.error(f"     错误: {result['error']}")

    # 总体统计
    total_tests = len(results)
    total_passed = sum(1 for r in results if r["passed"])
    total_failed = total_tests - total_passed

    logger.info("-" * 60)
    logger.info(f"总测试数: {total_tests}")
    logger.info(f"通过: {total_passed}")
    logger.info(f"失败: {total_failed}")
    logger.info(f"通过率: {total_passed/total_tests*100:.1f}%")
    logger.info("=" * 60)

    return all_passed


async def main():
    """运行F-13完整测试"""
    try:
        results = await test_all_apis()
        all_passed = generate_report(results)

        if all_passed:
            logger.info("\n✅ F-13 所有API测试通过")
        else:
            logger.error("\n❌ F-13 部分API测试失败")
            raise AssertionError("部分API测试未通过")

    except Exception as e:
        logger.error(f"❌ F-13 测试失败: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
