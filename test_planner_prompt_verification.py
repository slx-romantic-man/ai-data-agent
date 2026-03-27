"""
验证planner_prompt.py的修复：
1. 确认prompt要求LLM生成endpoint参数
2. 确认示例展示了正确的嵌套结构
3. 确认没有硬编码的股票规则
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.agent.prompts.planner_prompt import PLANNER_PROMPT, get_planner_prompt


def test_prompt_requires_endpoint():
    """测试1: Prompt要求api_fetch包含endpoint字段"""
    print("\n[Test 1] Prompt要求api_fetch包含endpoint字段")

    if "对于 api_fetch: 必须包含 \"endpoint\" 字段" in PLANNER_PROMPT:
        print("  [PASS] Prompt明确要求endpoint字段")
        return True
    else:
        print("  [FAIL] Prompt未要求endpoint字段")
        return False


def test_example_shows_nested_structure():
    """测试2: 示例展示正确的嵌套params结构"""
    print("\n[Test 2] 示例展示嵌套params结构")

    # 检查示例中是否有嵌套的params结构
    if '"endpoint":' in PLANNER_PROMPT and '"params": {' in PLANNER_PROMPT:
        # 检查是否在同一个params对象内
        lines = PLANNER_PROMPT.split('\n')
        found_nested = False
        for i, line in enumerate(lines):
            if '"endpoint":' in line:
                # 向后查找几行，看是否有嵌套的params
                for j in range(i, min(i+5, len(lines))):
                    if '"params": {' in lines[j] and j > i:
                        found_nested = True
                        break

        if found_nested:
            print("  [PASS] 示例展示了endpoint和params的嵌套结构")
            return True
        else:
            print("  [FAIL] 示例未展示嵌套结构")
            return False
    else:
        print("  [FAIL] 示例缺少endpoint或params")
        return False


def test_no_hardcoded_stock_rules():
    """测试3: 确认没有硬编码的股票规则"""
    print("\n[Test 3] 确认没有硬编码的股票规则")

    # 检查是否有针对股票的特殊规则
    forbidden_patterns = [
        "stock_symbol",
        "trading_day_count",
        "股票查询示例（当extracted_filters包含",
        "对于股票查询"
    ]

    found_hardcoded = []
    for pattern in forbidden_patterns:
        if pattern in PLANNER_PROMPT:
            found_hardcoded.append(pattern)

    if found_hardcoded:
        print(f"  [FAIL] 发现硬编码的股票规则: {found_hardcoded}")
        return False
    else:
        print("  [PASS] 没有硬编码的股票规则")
        return True


def test_example_is_generic():
    """测试4: 示例是通用的API调用示例"""
    print("\n[Test 4] 示例是通用的API调用示例")

    if "API调用示例" in PLANNER_PROMPT or "api_fetch示例" in PLANNER_PROMPT:
        print("  [PASS] 示例标题是通用的")
        return True
    else:
        print("  [FAIL] 示例标题不是通用的")
        return False


def test_get_planner_prompt_function():
    """测试5: get_planner_prompt函数能正常工作"""
    print("\n[Test 5] get_planner_prompt函数能正常工作")

    try:
        retrieved_apis = [{
            "config_id": "test_api",
            "name": "Test API",
            "description": "Test description",
            "endpoints": {
                "test_endpoint": {
                    "description": "Test endpoint",
                    "path": "/test"
                }
            }
        }]

        prompt = get_planner_prompt(
            user_query="测试查询",
            extracted_filters={},
            retrieved_apis=retrieved_apis
        )

        if prompt and len(prompt) > 0:
            print("  [PASS] get_planner_prompt函数正常工作")
            return True
        else:
            print("  [FAIL] get_planner_prompt返回空结果")
            return False
    except Exception as e:
        print(f"  [FAIL] get_planner_prompt抛出异常: {e}")
        return False


if __name__ == "__main__":
    print("="*70)
    print("Planner Prompt修复验证")
    print("="*70)

    results = []
    results.append(("Prompt要求endpoint", test_prompt_requires_endpoint()))
    results.append(("示例展示嵌套结构", test_example_shows_nested_structure()))
    results.append(("无硬编码股票规则", test_no_hardcoded_stock_rules()))
    results.append(("示例是通用的", test_example_is_generic()))
    results.append(("函数正常工作", test_get_planner_prompt_function()))

    print("\n" + "="*70)
    print("测试结果汇总")
    print("="*70)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {name}")

    all_passed = all(r[1] for r in results)

    if all_passed:
        print("\n[SUCCESS] 所有验证通过")
        sys.exit(0)
    else:
        print("\n[FAILURE] 部分验证失败")
        sys.exit(1)
