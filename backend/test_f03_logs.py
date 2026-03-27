"""
Test F-03: Verify API metadata passing by checking logs
"""
import time
import sys

def test_api_metadata_from_logs():
    """Test by checking recent planner logs for API metadata"""
    print("\n" + "="*60)
    print("F-03 Test: API Metadata Passing (Log Analysis)")
    print("="*60)

    print("\n1. Reading application logs...")
    try:
        with open('logs/app.log', 'r', encoding='utf-8') as f:
            logs = f.readlines()
    except Exception as e:
        print(f"   ERROR: Could not read logs: {e}")
        return False

    # Find recent Planner prompts
    print("\n2. Searching for recent Planner prompts...")
    planner_prompts = []
    for i, line in enumerate(logs):
        if '[PlannerNode] Prompt sent to LLM' in line:
            # Collect next few lines that contain the prompt
            prompt_lines = []
            for j in range(i, min(i+100, len(logs))):
                prompt_lines.append(logs[j])
                if '[PlannerNode] LLM Response' in logs[j]:
                    break
            planner_prompts.append(''.join(prompt_lines))

    if not planner_prompts:
        print("   WARNING: No Planner prompts found in logs")
        print("   Please run a query first to generate logs")
        return False

    print(f"   Found {len(planner_prompts)} Planner prompt(s)")

    # Analyze the most recent prompt
    print("\n3. Analyzing most recent Planner prompt...")
    latest_prompt = planner_prompts[-1]

    # Check for API metadata indicators
    checks = {
        "API ID present": "API ID:" in latest_prompt,
        "API name present": ("名称:" in latest_prompt or "Name:" in latest_prompt),
        "API description present": ("描述:" in latest_prompt or "Description:" in latest_prompt),
        "Endpoints present": ("可用端点:" in latest_prompt or "endpoints" in latest_prompt.lower()),
        "Parameters present": ("参数:" in latest_prompt or "params" in latest_prompt.lower() or "Parameters:" in latest_prompt),
    }

    all_passed = True
    for check_name, result in checks.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"   {status} {check_name}")
        if not result:
            all_passed = False

    # Show a sample of the prompt
    print("\n4. Sample of Planner prompt (first 500 chars):")
    print("   " + "-"*56)
    sample = latest_prompt[:500].replace('\n', '\n   ')
    print(f"   {sample}...")
    print("   " + "-"*56)

    # Final result
    print("\n" + "="*60)
    if all_passed:
        print("PASS: F-03 test passed - API metadata is complete")
        print("="*60)
        return True
    else:
        print("FAIL: F-03 test failed - API metadata is incomplete")
        print("="*60)
        print("\nDEBUG: Full latest prompt:")
        print(latest_prompt)
        return False


if __name__ == "__main__":
    result = test_api_metadata_from_logs()
    sys.exit(0 if result else 1)
