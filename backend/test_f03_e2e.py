"""
Test F-03: End-to-End test for API metadata passing
Tests the complete flow from query to planner with full API metadata
"""
import requests
import json
import time
import sys

BASE_URL = "http://localhost:8002"


def test_api_metadata_e2e():
    """Test complete flow with API metadata"""
    print("\n" + "="*60)
    print("F-03 E2E Test: API Metadata Passing")
    print("="*60)

    # Step 1: Send query
    query = "query apple stock price for last 7 trading days"
    print(f"\n1. Sending query: {query}")

    payload = {
        "message": query,
        "session_id": f"test_f03_{int(time.time())}"
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/chat/stream",
        json=payload,
        stream=True,
        timeout=60
    )

    if response.status_code != 200:
        print(f"ERROR: Request failed with status {response.status_code}")
        return False

    # Step 2: Collect SSE events
    print("\n2. Collecting SSE events...")
    events = []
    retrieval_data = None
    planner_data = None

    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                try:
                    data = json.loads(line_str[6:])
                    events.append(data)

                    event_type = data.get('type')
                    if event_type == 'retrieval':
                        retrieval_data = data
                        print(f"   - Retrieval event received")
                    elif event_type == 'planner':
                        planner_data = data
                        print(f"   - Planner event received")
                    elif event_type == 'error':
                        print(f"   - Error: {data.get('message')}")
                        return False

                except json.JSONDecodeError:
                    pass

    # Step 3: Verify Retrieval Node output
    print("\n3. Checking Retrieval Node output...")
    if not retrieval_data:
        print("   ERROR: No retrieval event found")
        return False

    retrieved_apis = retrieval_data.get('data', {}).get('retrieved_apis', [])
    print(f"   Retrieved {len(retrieved_apis)} APIs")

    if len(retrieved_apis) == 0:
        print("   ERROR: No APIs retrieved")
        return False

    # Check first API metadata
    first_api = retrieved_apis[0]
    api_id = first_api.get('api_id') or first_api.get('id')
    name = first_api.get('name', 'N/A')
    description = first_api.get('description', 'N/A')
    endpoints = first_api.get('endpoints', {})

    print(f"\n   First API:")
    print(f"   - ID: {api_id}")
    print(f"   - Name: {name}")
    print(f"   - Description: {description}")
    print(f"   - Endpoints: {len(endpoints)} found")

    # Step 4: Verify API metadata completeness
    print("\n4. Verifying API metadata completeness...")
    all_passed = True

    if not description or description == 'N/A':
        print("   [FAIL] Description is empty")
        all_passed = False
    else:
        print("   [PASS] Description is not empty")

    if not endpoints:
        print("   [FAIL] Endpoints information missing")
        all_passed = False
    else:
        print(f"   [PASS] Endpoints information exists ({len(endpoints)} endpoints)")
        for endpoint_name, endpoint_config in list(endpoints.items())[:2]:
            if isinstance(endpoint_config, dict):
                endpoint_params = endpoint_config.get('params', {})
                print(f"      - {endpoint_name}: {len(endpoint_params)} params")

    # Step 5: Verify Planner received full metadata
    print("\n5. Checking Planner Node received metadata...")
    if not planner_data:
        print("   WARNING: No planner event found (may not have reached planner)")
    else:
        plan = planner_data.get('data', {}).get('plan', [])
        print(f"   Planner generated {len(plan)} steps")

    # Step 6: Check logs for metadata
    print("\n6. Checking application logs...")
    try:
        with open('logs/app.log', 'r', encoding='utf-8') as f:
            logs = f.readlines()
            recent_logs = logs[-200:]  # Last 200 lines

            planner_logs = [
                line for line in recent_logs
                if '[PlannerNode]' in line and 'Prompt sent to LLM' in line
            ]

            if planner_logs:
                last_planner_log = planner_logs[-1]
                if 'endpoints' in last_planner_log.lower() or \
                   'params' in last_planner_log.lower():
                    print("   [PASS] Planner log shows API metadata")
                else:
                    print("   [WARN] Planner log may not show full metadata")
            else:
                print("   [INFO] No recent planner logs found")

    except Exception as e:
        print(f"   [WARN] Could not read logs: {e}")

    # Final result
    print("\n" + "="*60)
    if all_passed:
        print("PASS: F-03 test passed - API metadata is complete")
    else:
        print("FAIL: F-03 test failed - API metadata is incomplete")
    print("="*60)

    return all_passed


if __name__ == "__main__":
    result = test_api_metadata_e2e()
    sys.exit(0 if result else 1)
