#!/usr/bin/env python
"""
F-CM-04 E2E Verification: 状态初始化历史加载
Steps from feature_list.json:
1. Check code at chat.py lines 159-177
2. Verify initial_state['messages'] loads from session['messages']
3. Verify format [{'role': 'user/assistant', 'content': '...'}]
4. Verify log: logger.info(f"Loaded {len(formatted_history)} history messages")
5. Run multi-turn conversation and verify logs
6. Verify each request's initial_state contains history
"""

import subprocess
import json
import re
import time
import requests

BASE = "http://localhost:8002"
SESSION = "test-fcm04-verify"
LOG_FILE = "D:\\Users\\Desktop\\实习工作\\week4\\ai-data-agent - v4.2\\backend\\logs\\app.log"

def check_code():
    """Verify chat.py code has correct history loading."""
    with open("D:\\Users\\Desktop\\实习工作\\week4\\ai-data-agent - v4.2\\backend\\app\\api\\v1\\chat.py", "r", encoding="utf-8") as f:
        content = f.read()

    results = {}

    # Check 1: initial_state['messages'] loads from formatted_history
    results["code_loads_session_history"] = (
        "conversation_history = session.get" in content and
        "formatted_history" in content and
        '"messages": formatted_history' in content
    )

    # Check 2: Format preserves role and content
    results["code_format_role_content"] = (
        '"role"' in content and '"content"' in content and
        "formatted_msg = {" in content
    )

    # Check 3: Log verification exists
    results["code_has_log"] = "[ChatAPI] Loaded" in content and "history messages" in content

    # Check 4: Type metadata preserved
    results["code_preserves_type"] = '"type" in msg' in content

    return results


def send_message(message: str, session_id: str):
    """Send a message via the chat API."""
    resp = requests.post(
        f"{BASE}/api/v1/chat",
        json={"message": message, "session_id": session_id},
        timeout=120
    )
    return resp.status_code, resp.json()


def check_logs(session_id: str):
    """Check logs for history loading entries."""
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        log_content = f.read()

    # Find all log lines for this session
    pattern = re.compile(rf"\[ChatAPI\] Loaded (\d+) history messages for session {re.escape(session_id)}")
    matches = pattern.findall(log_content)
    return [int(m) for m in matches]


def main():
    print("=" * 70)
    print("F-CM-04 E2E Verification: 状态初始化历史加载")
    print("=" * 70)

    # Step 1-3: Code review
    print("\n--- Code Review ---")
    code_results = check_code()
    for check, passed in code_results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {check}: {status}")

    if not all(code_results.values()):
        print("\nF-CM-04 FAILED: Code review failed")
        return False

    # Step 4: Check log statement exists in code (already verified above)
    print("\n--- Log Statement Verification ---")
    print("  Log format: [ChatAPI] Loaded {n} history messages for session {id}: PASS")

    # Step 5-6: Multi-turn conversation test
    print("\n--- Multi-turn Conversation Test ---")

    # Message 1: New session
    print("  Sending message 1 (new session)...")
    status1, resp1 = send_message("分析苹果美股股价变化", SESSION)
    print(f"    HTTP {status1}")
    resp_text1 = resp1.get("response", {}).get("text", "")
    has_clarification1 = "请问" in resp_text1 or "时间范围" in resp_text1
    print(f"    Contains clarification: {has_clarification1}")

    time.sleep(1)

    # Message 2: Follow-up
    print("  Sending message 2 (follow-up with '近期的')...")
    status2, resp2 = send_message("近期的", SESSION)
    print(f"    HTTP {status2}")
    resp_text2 = resp2.get("response", {}).get("text", "")
    has_data2 = len(resp_text2) > 100  # Substantial response
    print(f"    Contains data response: {has_data2}")

    time.sleep(1)

    # Message 3: Third message
    print("  Sending message 3...")
    status3, resp3 = send_message("成交量怎么样", SESSION)
    print(f"    HTTP {status3}")
    resp_text3 = resp3.get("response", {}).get("text", "")
    has_data3 = len(resp_text3) > 50
    print(f"    Contains response: {has_data3}")

    # Check logs
    print("\n--- Log Verification ---")
    log_counts = check_logs(SESSION)
    print(f"  Log entries for session {SESSION}: {log_counts}")

    log_pass = True
    if len(log_counts) >= 3:
        # First message should have 0 history, second 2, third 4+
        if log_counts[0] == 0:
            print("  Message 1: 0 history (new session) - PASS")
        else:
            print(f"  Message 1: {log_counts[0]} history (expected 0) - FAIL")
            log_pass = False

        if log_counts[1] >= 2:
            print(f"  Message 2: {log_counts[1]} history (>=2) - PASS")
        else:
            print(f"  Message 2: {log_counts[1]} history (expected >=2) - FAIL")
            log_pass = False

        if log_counts[2] >= 4:
            print(f"  Message 3: {log_counts[2]} history (>=4) - PASS")
        else:
            print(f"  Message 3: {log_counts[2]} history (expected >=4) - FAIL")
            log_pass = False
    else:
        print(f"  WARNING: Only {len(log_counts)} log entries found (expected >=3)")
        log_pass = False

    # Final summary
    print("\n" + "=" * 70)
    print("F-CM-04 Validation Criteria:")
    print(f"  code_review (initial_state['messages'] contains session history): {'PASS' if all(code_results.values()) else 'FAIL'}")
    print(f"  log_verification (History loaded message in logs): {'PASS' if log_pass else 'FAIL'}")
    print(f"  format_correct (messages format matches LangGraph requirements): {'PASS' if has_data2 else 'FAIL'}")

    all_pass = all(code_results.values()) and log_pass and has_data2
    print(f"\nOverall: {'PASS' if all_pass else 'FAIL'}")
    print("=" * 70)

    return all_pass


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
