"""
F-10 Simple Test: Planner Fallback Safety
Tests fallback behavior without requiring LLM calls
"""
from app.agent.nodes.planner_node import _create_fallback_plan, _parse_and_validate_plan


def test_fallback_with_valid_api():
    """Test 1: Fallback with valid API metadata"""
    print("\n" + "="*60)
    print("Test 1: Fallback with valid API metadata")
    print("="*60)

    retrieved_apis = [{
        "api_id": 4,
        "config_id": "alpha_vantage_stock",
        "name": "Alpha Vantage Stock Query",
        "description": "Query stock prices",
        "endpoint": "https://www.alphavantage.co/query"
    }]

    plan = _create_fallback_plan("query stock", retrieved_apis)

    if not plan:
        print("[FAIL] Fallback should generate plan with valid API")
        return False

    if len(plan) != 1:
        print(f"[FAIL] Expected 1 step, got {len(plan)}")
        return False

    step = plan[0]
    if step['api_id'] != 'alpha_vantage_stock':
        print(f"[FAIL] Expected api_id='alpha_vantage_stock', got '{step['api_id']}'")
        return False

    if 'unknown' in str(step['api_id']).lower():
        print(f"[FAIL] api_id contains 'unknown': {step['api_id']}")
        return False

    print(f"[PASS] Generated valid plan: api_id={step['api_id']}")
    return True


def test_fallback_without_api():
    """Test 2: Fallback without API metadata"""
    print("\n" + "="*60)
    print("Test 2: Fallback without API metadata")
    print("="*60)

    plan = _create_fallback_plan("query data", [])

    if plan and len(plan) > 0:
        print(f"[FAIL] Should return empty plan, got {len(plan)} steps")
        return False

    print("[PASS] Correctly returned empty plan")
    return True


def test_fallback_with_missing_config_id():
    """Test 3: Fallback with API missing config_id"""
    print("\n" + "="*60)
    print("Test 3: Fallback with API missing config_id")
    print("="*60)

    retrieved_apis = [{
        "api_id": 999,
        "name": "Broken API",
        "description": "API without config_id"
        # Missing config_id
    }]

    plan = _create_fallback_plan("query data", retrieved_apis)

    if plan and len(plan) > 0:
        print(f"[FAIL] Should return empty plan for API without config_id, got {len(plan)} steps")
        return False

    print("[PASS] Correctly refused to generate plan without config_id")
    return True


def test_fallback_rejects_unknown():
    """Test 4: Fallback rejects 'unknown' in api_id"""
    print("\n" + "="*60)
    print("Test 4: Fallback rejects 'unknown' in api_id")
    print("="*60)

    retrieved_apis = [{
        "api_id": 999,
        "config_id": "unknown_api",
        "name": "Unknown API",
        "description": "API with unknown identifier"
    }]

    plan = _create_fallback_plan("query data", retrieved_apis)

    if plan and len(plan) > 0:
        print(f"[FAIL] Should reject API with 'unknown' in config_id, got {len(plan)} steps")
        return False

    print("[PASS] Correctly rejected API with 'unknown' identifier")
    return True


def test_parse_valid_json():
    """Test 5: Parse valid JSON plan"""
    print("\n" + "="*60)
    print("Test 5: Parse valid JSON plan")
    print("="*60)

    valid_response = '''
    {
        "steps": [
            {
                "step_id": 1,
                "tool": "api_fetch",
                "api_id": "test_api",
                "params": {},
                "description": "Test step",
                "depends_on": []
            }
        ],
        "reasoning": "Test reasoning"
    }
    '''

    plan = _parse_and_validate_plan(valid_response)

    if not plan:
        print("[FAIL] Should parse valid JSON")
        return False

    if len(plan) != 1:
        print(f"[FAIL] Expected 1 step, got {len(plan)}")
        return False

    print("[PASS] Successfully parsed valid JSON plan")
    return True


def test_parse_invalid_json():
    """Test 6: Parse invalid JSON returns None"""
    print("\n" + "="*60)
    print("Test 6: Parse invalid JSON returns None")
    print("="*60)

    invalid_response = "This is not JSON at all"

    plan = _parse_and_validate_plan(invalid_response)

    if plan is not None:
        print(f"[FAIL] Should return None for invalid JSON, got {plan}")
        return False

    print("[PASS] Correctly returned None for invalid JSON")
    return True


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("F-10 Planner Fallback Safety Tests")
    print("="*80)

    tests = [
        ("Test 1: Fallback with valid API", test_fallback_with_valid_api),
        ("Test 2: Fallback without API", test_fallback_without_api),
        ("Test 3: Fallback with missing config_id", test_fallback_with_missing_config_id),
        ("Test 4: Fallback rejects unknown", test_fallback_rejects_unknown),
        ("Test 5: Parse valid JSON", test_parse_valid_json),
        ("Test 6: Parse invalid JSON", test_parse_invalid_json),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"[ERROR] Test failed with exception: {e}")
            results.append((name, False))

    # Summary
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
    success = main()
    exit(0 if success else 1)
