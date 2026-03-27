"""
F-10 测试：Planner Fallback 安全化
测试场景：
1. LLM 返回非法 JSON 但有足够 API 元数据 -> 应生成最小合法计划
2. LLM 返回非法 JSON 且无 API 元数据 -> 应明确失败
3. 验证 fallback 不会生成 unknown api_id
"""
import asyncio
from app.agent.nodes.planner_node import planner_node, _parse_and_validate_plan, _create_fallback_plan
from app.agent.state import AgentState


async def test_fallback_with_valid_apis():
    """场景1：LLM失败但有足够API元数据，应生成最小合法计划"""
    print("\n" + "="*60)
    print("场景1：Fallback with valid API metadata")
    print("="*60)

    state: AgentState = {
        "messages": [],
        "query": "查询贵州茅台股价",
        "extracted_filters": {},
        "plan": [],
        "current_step": 0,
        "data_context": {},
        "permission": {"user_id": "user1", "role": "employee"}
    }

    retrieved_apis = [{
        "api_id": 4,
        "config_id": "alpha_vantage_stock",
        "name": "Alpha Vantage 股票查询",
        "description": "查询股票实时价格和历史数据",
        "endpoint": "https://www.alphavantage.co/query"
    }]

    # 模拟 LLM 返回非法响应，触发 fallback
    invalid_response = "这是一个无效的响应，没有JSON"
    plan = _parse_and_validate_plan(invalid_response)

    if not plan:
        print("[PASS] LLM parsing failed, triggering fallback")
        fallback_plan = _create_fallback_plan(state["query"], retrieved_apis)

        if fallback_plan:
            print(f"[PASS] Fallback generated plan: {len(fallback_plan)} steps")
            for step in fallback_plan:
                print(f"  - Step {step['step_id']}: {step['tool']} | api_id={step['api_id']}")

                # Verify api_id is not unknown
                if step['api_id'] == 'unknown' or 'unknown' in str(step['api_id']).lower():
                    print(f"[FAIL] api_id contains 'unknown': {step['api_id']}")
                    return False

                # Verify api_id is string
                if not isinstance(step['api_id'], str):
                    print(f"[FAIL] api_id is not string: {type(step['api_id'])}")
                    return False

            print("[PASS] Fallback generated valid plan with correct api_id")
            return True
        else:
            print("[FAIL] Fallback did not generate plan")
            return False


async def test_fallback_without_apis():
    """场景2：LLM失败且无API元数据，应明确失败"""
    print("\n" + "="*60)
    print("场景2：Fallback without API metadata - should fail explicitly")
    print("="*60)

    state: AgentState = {
        "messages": [],
        "query": "查询不存在的数据",
        "extracted_filters": {},
        "plan": [],
        "current_step": 0,
        "data_context": {},
        "permission": {"user_id": "user1", "role": "employee"}
    }

    retrieved_apis = []  # 没有可用 API

    # 触发 fallback
    fallback_plan = _create_fallback_plan(state["query"], retrieved_apis)

    if not fallback_plan or len(fallback_plan) == 0:
        print("[PASS] Fallback correctly returned empty plan (no APIs available)")
        return True
    else:
        print(f"[FAIL] Fallback should not generate plan, but generated {len(fallback_plan)} steps")
        return False


async def test_planner_node_with_fallback():
    """场景3：完整 planner_node 流程测试"""
    print("\n" + "="*60)
    print("场景3：Complete planner_node with fallback")
    print("="*60)

    state: AgentState = {
        "messages": [],
        "query": "查询贵州茅台股价",
        "extracted_filters": {},
        "plan": [],
        "current_step": 0,
        "data_context": {},
        "permission": {"user_id": "user1", "role": "employee"}
    }

    retrieved_apis = [{
        "api_id": 4,
        "config_id": "alpha_vantage_stock",
        "name": "Alpha Vantage 股票查询",
        "description": "查询股票实时价格和历史数据",
        "endpoint": "https://www.alphavantage.co/query"
    }]

    # 注意：这会真实调用 LLM，可能成功也可能失败
    # 我们主要验证无论如何都不会生成 unknown api_id
    result_state = await planner_node(state, retrieved_apis)

    if "error" in result_state:
        print(f"[INFO] Planner returned error: {result_state['error']}")
        if not result_state.get("plan"):
            print("[PASS] No fake plan generated in error case")
            return True
        else:
            print("[FAIL] Should not generate plan in error case")
            return False

    plan = result_state.get("plan", [])
    if not plan:
        print("[INFO] No plan generated")
        return True

    print(f"Generated {len(plan)} step plan")
    for step in plan:
        print(f"  - Step {step['step_id']}: {step['tool']} | api_id={step.get('api_id', 'N/A')}")

        # Verify no unknown
        if step.get('api_id') and ('unknown' in str(step['api_id']).lower()):
            print(f"[FAIL] api_id contains 'unknown': {step['api_id']}")
            return False

    print("[PASS] Plan does not contain unknown api_id")
    return True


async def main():
    """运行所有测试"""
    print("\n" + "="*80)
    print("F-10 Planner Fallback 安全化测试")
    print("="*80)

    results = []

    # 测试1
    result1 = await test_fallback_with_valid_apis()
    results.append(("场景1: Fallback with APIs", result1))

    # 测试2
    result2 = await test_fallback_without_apis()
    results.append(("场景2: Fallback without APIs", result2))

    # 测试3
    result3 = await test_planner_node_with_fallback()
    results.append(("场景3: Complete planner_node", result3))

    # 汇总
    print("\n" + "="*80)
    print("Test Results Summary")
    print("="*80)
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} - {name}")

    all_passed = all(r for _, r in results)
    print("\n" + "="*80)
    if all_passed:
        print("[SUCCESS] All tests passed")
    else:
        print("[FAILURE] Some tests failed")
    print("="*80)

    return all_passed


if __name__ == "__main__":
    asyncio.run(main())
