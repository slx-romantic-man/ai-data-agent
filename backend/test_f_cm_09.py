"""
F-CM-09 E2E Test: 边界测试 - 用户补充无关信息时系统应识别并重新询问
"""
import requests
import json
import time
import sys

BASE_URL = "http://localhost:8002"
SESSION_ID = "test-fcm09-edge"


def test_f_cm_09():
    """Test that the system identifies irrelevant user responses and re-asks."""
    print("=" * 60)
    print("F-CM-09: 边界测试 - 用户补充无关信息时系统应识别并重新询问")
    print("=" * 60)

    # Step 1: 发送"查询订单量"
    print("\n--- Step 1: 发送'查询订单量' ---")
    r = requests.post(f"{BASE_URL}/api/v1/chat", json={
        "message": "查询订单量",
        "session_id": SESSION_ID
    })
    assert r.status_code == 200, f"Step 1: Expected 200, got {r.status_code}"
    data1 = r.json()
    text1 = data1["response"]["text"]
    print(f"Response: {text1}")

    # Verify clarification question
    has_clarification = "请问" in text1 or "时间" in text1
    assert has_clarification, "Step 1: Expected clarification question about time range"
    print("Step 1: PASS - Received clarification question\n")

    time.sleep(1)

    # Step 2: 发送无关补充"我想吃苹果"
    print("--- Step 2: 发送无关补充'我想吃苹果' ---")
    r = requests.post(f"{BASE_URL}/api/v1/chat", json={
        "message": "我想吃苹果",
        "session_id": SESSION_ID
    })
    assert r.status_code == 200, f"Step 2: Expected 200, got {r.status_code}"
    data2 = r.json()
    text2 = data2["response"]["text"]
    print(f"Response: {text2}")

    # Validation Criteria
    print("\n--- Validation Criteria ---")

    # 1. intent_discrimination: 系统识别补充信息无关，重新询问时间范围
    intent_discrimination = "时间" in text2 or "范围" in text2 or "time" in text2.lower()
    print(f"1. intent_discrimination: {'PASS' if intent_discrimination else 'FAIL'}")

    # 2. no_wrong_execution: 不误执行"苹果股价"查询
    no_wrong_execution = "股价" not in text2 and "stock" not in text2.lower() and "AAPL" not in text2
    print(f"2. no_wrong_execution: {'PASS' if no_wrong_execution else 'FAIL'}")

    # 3. appropriate_re_ask: 重新询问时间范围
    appropriate_re_ask = "请问" in text2 or "时间" in text2 or "范围" in text2
    print(f"3. appropriate_re_ask: {'PASS' if appropriate_re_ask else 'FAIL'}")

    # Check session
    try:
        with open("backend/sessions.json", "r", encoding="utf-8") as f:
            sessions = json.load(f)
        session = sessions.get(SESSION_ID, {})
        msgs = session.get("messages", [])
        print(f"\nSession messages count: {len(msgs)}")
        for i, m in enumerate(msgs):
            content = m.get("content", "")[:80]
            msg_type = m.get("type", "")
            print(f"  [{i}] {m['role']} (type={msg_type}): {content}")

        session_correct = len(msgs) >= 4  # At least 2 user + 2 assistant
    except Exception as e:
        print(f"\nWarning: Could not read sessions.json: {e}")
        session_correct = False
        print(f"\n4. session_history_correct: FAIL (read error)")

    all_pass = all([intent_discrimination, no_wrong_execution, appropriate_re_ask, session_correct])
    print(f"\n{'=' * 60}")
    print(f"F-CM-09 Result: {'ALL PASS' if all_pass else 'SOME FAIL'}")
    print(f"{'=' * 60}")

    return all_pass


if __name__ == "__main__":
    try:
        success = test_f_cm_09()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Test error: {e}")
        sys.exit(1)
