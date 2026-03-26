"""
Test F-02: Intent Node 股票实体与交易日语义识别能力测试
"""
import asyncio
import json
from app.agent.nodes.intent_node import intent_clarification_node
from app.agent.state import AgentState


async def test_stock_intent_extraction():
    """测试股票查询的意图提取"""
    print("=" * 60)
    print("F-02 测试：Intent Node 股票实体识别")
    print("=" * 60)

    # 构造测试状态
    state: AgentState = {
        "messages": [],
        "query": "苹果的美股股价最近7个交易日",
        "extracted_filters": None,
        "plan": None,
        "current_step": 0,
        "data_context": {},
        "requires_approval": False
    }

    print(f"\n[TEST] Query: {state['query']}")
    print("\n[TEST] Calling Intent Node...")

    # 调用 Intent Node
    result_state = await intent_clarification_node(state)

    # 检查结果
    extracted = result_state.get("extracted_filters")

    if not extracted:
        print("\n[FAIL] No extracted_filters found")
        return False

    print("\n[PASS] Extracted filters:")
    print(json.dumps(extracted, ensure_ascii=False, indent=2))

    # 验证必需字段
    entities = extracted.get("entities", {})

    checks = {
        "stock_symbol": entities.get("stock_symbol"),
        "market": entities.get("market"),
        "trading_day_count": entities.get("trading_day_count")
    }

    print("\n[TEST] Field validation:")
    all_passed = True
    for field, value in checks.items():
        status = "[PASS]" if value else "[FAIL]"
        print(f"  {status} {field}: {value}")
        if not value:
            all_passed = False

    if all_passed:
        print("\n[PASS] F-02 test passed: all required fields extracted")
        return True
    else:
        print("\n[FAIL] F-02 test failed: some fields missing")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_stock_intent_extraction())
    exit(0 if result else 1)
