"""F-CM-06 E2E test: Prompt template history field verification"""
import requests
import json
import time
import os
import sys
from pathlib import Path

BASE_URL = "http://localhost:8002"
PROJECT_ROOT = Path(__file__).parent.parent
SESSION_ID = "test-fcm06-session"

def test_function_signature():
    """Step 1-2: Verify get_intent_prompt has history parameter"""
    print("\n=== Step 1-2: Function Signature Check ===")

    sys.path.insert(0, str(PROJECT_ROOT))
    from app.agent.prompts.intent_prompt import get_intent_prompt
    import inspect

    sig = inspect.signature(get_intent_prompt)
    params = list(sig.parameters.keys())
    print(f"  Parameters: {params}")

    assert 'history' in params, "FAIL: history parameter missing"
    param = sig.parameters['history']
    assert param.default is None, "FAIL: history default should be None"
    print("  PASS: get_intent_prompt(query, api_list, history=None)")
    return True

def test_prompt_template():
    """Step 3-4: Verify prompt has ### 对话历史 section"""
    print("\n=== Step 3-4: Prompt Template Check ===")

    sys.path.insert(0, str(PROJECT_ROOT))
    from app.agent.prompts.intent_prompt import get_intent_prompt

    history = [
        {"role": "user", "content": "分析苹果股价"},
        {"role": "assistant", "content": "请问您想分析哪个时间范围？", "type": "clarification"},
    ]

    prompt = get_intent_prompt("近期的", "test_api_list", history=history)

    assert "### 对话历史" in prompt, "FAIL: ### 对话历史 section missing"
    assert "结合历史上下文" in prompt, "FAIL: history instruction missing"
    assert "分析苹果股价" in prompt, "FAIL: history content not included"
    print("  PASS: ### 对话历史 section exists with correct content")
    return True

def test_intent_node_passes_history():
    """Step 5-6: Verify intent_node passes messages to get_intent_prompt"""
    print("\n=== Step 5-6: Intent Node History Passing Check ===")

    sys.path.insert(0, str(PROJECT_ROOT))
    from app.agent.nodes.intent_node import intent_clarification_node
    import inspect

    source = inspect.getsource(intent_clarification_node)
    assert "history=" in source, "FAIL: history= parameter not passed"
    assert "get_intent_prompt" in source, "FAIL: get_intent_prompt not called"

    # Check the actual call pattern
    assert "history=messages" in source, "FAIL: state['messages'] not passed to prompt"
    print("  PASS: intent_node passes state['messages'] to get_intent_prompt")
    return True

def test_e2e_history_in_prompt():
    """Step 7: E2E - Verify history reaches LLM via log inspection"""
    print("\n=== Step 7: E2E History in Prompt Check ===")

    # Send a clarification follow-up and check the prompt includes history
    # We'll use a log-based approach since we can't directly inspect the prompt

    # First, send initial query
    resp1 = requests.post(f"{BASE_URL}/api/v1/chat", json={
        "message": "分析苹果美股股价变化",
        "session_id": SESSION_ID
    }, timeout=60)

    print(f"  Response 1 status: {resp1.status_code}")
    data1 = resp1.json()
    print(f"  Response 1 content (truncated): {data1.get('content', '')[:100]}")

    if resp1.status_code != 200:
        print(f"  FAIL: First request failed")
        return False

    # Check that first response is a clarification
    content1 = data1.get('content', '')
    if '时间范围' not in content1 and '请问' not in content1:
        print(f"  WARN: Expected clarification question, got: {content1[:100]}")

    # Send clarification follow-up
    resp2 = requests.post(f"{BASE_URL}/api/v1/chat", json={
        "message": "近期的",
        "session_id": SESSION_ID
    }, timeout=120)

    print(f"  Response 2 status: {resp2.status_code}")
    if resp2.status_code != 200:
        print(f"  FAIL: Second request failed")
        return False

    data2 = resp2.json()
    content2 = data2.get('content', '')
    print(f"  Response 2 content (truncated): {content2[:200]}")

    # Check log for history-related entries
    log_file = PROJECT_ROOT / "logs" / "app.log"
    if log_file.exists():
        log_content = log_file.read_text(errors='replace')
        # Look for evidence that history was loaded and used
        loaded_count = log_content.count("Loaded")
        print(f"  Log 'Loaded' entries: {loaded_count}")

    # If we get a data response (not another clarification), history was used
    has_data = any(kw in content2 for kw in ['股价', 'AAPL', '价格', '涨跌幅', '趋势', '分析', '数据'])
    not_clarification = '请问' not in content2

    if has_data and not_clarification:
        print("  PASS: Second response contains data (history was used for context)")
        return True
    else:
        print(f"  WARN: Second response may still be a clarification")
        return False

if __name__ == "__main__":
    print("="*60)
    print("F-CM-06 E2E Test: Prompt Template History Field")
    print("="*60)

    results = {}

    # Code review tests
    try:
        results['function_signature'] = test_function_signature()
    except Exception as e:
        print(f"  FAIL: {e}")
        results['function_signature'] = False

    try:
        results['prompt_template'] = test_prompt_template()
    except Exception as e:
        print(f"  FAIL: {e}")
        results['prompt_template'] = False

    try:
        results['intent_node_passes_history'] = test_intent_node_passes_history()
    except Exception as e:
        print(f"  FAIL: {e}")
        results['intent_node_passes_history'] = False

    # E2E test
    try:
        results['e2e_history_in_prompt'] = test_e2e_history_in_prompt()
    except requests.exceptions.ConnectionError:
        print("  SKIP: Server not running")
        results['e2e_history_in_prompt'] = None
    except Exception as e:
        print(f"  FAIL: {e}")
        results['e2e_history_in_prompt'] = False

    # Summary
    print("\n" + "="*60)
    print("F-CM-06 Validation Criteria Results:")
    print("="*60)

    criteria_map = {
        'function_signature': 'function_signature',
        'prompt_template': 'prompt_template',
        'intent_node_passes_history': 'history_passed',
        'e2e_history_in_prompt': 'llm_context_complete'
    }

    all_pass = True
    for test_name, criterion in criteria_map.items():
        result = results.get(test_name)
        status = "PASS" if result is True else "FAIL" if result is False else "SKIP"
        if result is not True:
            all_pass = False
        print(f"  {criterion}: {status}")

    print(f"\nOverall: {'ALL PASS' if all_pass else 'SOME FAILED'}")
    sys.exit(0 if all_pass else 1)
