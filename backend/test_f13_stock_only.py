"""
F-13 股票API测试（仅测试有效的alpha_vantage_stock API）
测试3个复杂自然语言问题，验证Agent完整工作流
"""
import asyncio
import sys
from typing import Dict, List
from app.agent.graph import create_graph
from app.agent.state import AgentState
from app.models.permission import PermissionContext
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 设置stdout编码为utf-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


# 股票API测试问题
STOCK_TEST_QUESTIONS = [
    "查询苹果公司最近一周的股价走势，并分析涨跌幅度",
    "帮我看看特斯拉股票最近5个交易日的收盘价变化趋势",
    "IBM的股票在过去7天内表现如何？有没有明显的波动？"
]


def safe_print(text: str):
    """安全打印，处理编码问题和emoji"""
    try:
        # 移除emoji和特殊字符
        safe_text = text.encode('ascii', errors='ignore').decode('ascii')
        if not safe_text.strip():
            # 如果全是非ASCII字符，使用repr
            safe_text = repr(text)
        print(safe_text)
    except Exception as e:
        print(f"[Print Error: {e}]")


def validate_final_answer(result: AgentState, question: str) -> bool:
    """验证最终回答是否有效"""
    messages = result.get("messages", [])

    if not messages:
        logger.error(f"No messages in result")
        return False

    final_message = messages[-1]
    if not final_message:
        logger.error(f"Final message is empty")
        return False

    final_answer = final_message.get("content", "")
    if not final_answer or not final_answer.strip():
        logger.error(f"Final answer content is empty")
        return False

    if len(final_answer.strip()) < 10:
        logger.error(f"Final answer too short ({len(final_answer)} chars)")
        return False

    logger.info(f"[OK] Final answer valid ({len(final_answer)} chars)")
    logger.info(f"  Question: {question[:50]}...")
    logger.info(f"  Answer preview: {final_answer[:150]}...")

    return True


async def test_stock_question(question: str, test_index: int) -> Dict:
    """测试单个股票问题"""
    logger.info("=" * 60)
    logger.info(f"Test {test_index}/3: {question}")
    logger.info("=" * 60)

    permission = PermissionContext(
        user_id="1",
        role="admin",
        allowed_tables=[]
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

    config = {"configurable": {"thread_id": f"f13_stock_{test_index}"}}

    try:
        result = await graph.ainvoke(initial_state, config)
        passed = validate_final_answer(result, question)

        final_answer = result["messages"][-1]["content"] if result.get("messages") else None

        return {
            "question": question,
            "passed": passed,
            "final_answer": final_answer,
            "error": None
        }
    except Exception as e:
        logger.error(f"Test exception: {e}", exc_info=True)
        return {
            "question": question,
            "passed": False,
            "final_answer": None,
            "error": str(e)
        }


async def main():
    """运行股票API测试"""
    logger.info("\n" + "=" * 60)
    logger.info("F-13 Stock API Test (alpha_vantage_stock only)")
    logger.info("=" * 60 + "\n")

    results = []

    for idx, question in enumerate(STOCK_TEST_QUESTIONS, 1):
        result = await test_stock_question(question, idx)
        results.append(result)
        logger.info("")

    # 生成报告
    logger.info("\n" + "=" * 60)
    logger.info("Test Report")
    logger.info("=" * 60 + "\n")

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed

    logger.info(f"Total: {total} questions")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Pass rate: {passed/total*100:.1f}%")
    logger.info("")

    # 详细结果
    for idx, result in enumerate(results, 1):
        status = "[PASS]" if result["passed"] else "[FAIL]"
        logger.info(f"{status} Question {idx}: {result['question'][:60]}...")

        if result["passed"] and result["final_answer"]:
            logger.info(f"  Answer: {result['final_answer'][:200]}...")
        elif result["error"]:
            logger.error(f"  Error: {result['error']}")

    logger.info("\n" + "=" * 60)

    if passed == total:
        logger.info("[SUCCESS] All stock API tests passed!")
        return True
    else:
        logger.error(f"[FAILED] {failed}/{total} tests failed")
        raise AssertionError(f"F-13 stock test failed: {failed}/{total}")


if __name__ == "__main__":
    asyncio.run(main())
