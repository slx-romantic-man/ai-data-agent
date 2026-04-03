"""
E2E Test for F-CM-08: 回归测试 - 单轮完整查询不受影响
验证完整查询（如"今天北京天气"、"最近7天订单量"）直接执行，不触发不必要的澄清
"""
import requests
import json
import time
import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

BASE_URL = "http://localhost:8002"
SESSION_ID = "test-single-turn-fcm08"

def cleanup_session():
    try:
        sessions_file = "sessions.json"
        if os.path.exists(sessions_file):
            with open(sessions_file, "r", encoding="utf-8") as f:
                sessions = json.load(f)
            if SESSION_ID in sessions:
                del sessions[SESSION_ID]
                with open(sessions_file, "w", encoding="utf-8") as f:
                    json.dump(sessions, f, ensure_ascii=False, indent=2)
                print(f"[Cleanup] Removed previous session data")
    except Exception as e:
        print(f"[Cleanup] Warning: {e}")

def test_single_turn():
    print("=" * 60)
    print("F-CM-08: 回归测试 - 单轮完整查询不受影响")
    print("=" * 60)

    cleanup_session()

    # Step 1: Weather query with complete info
    print("\n[Step 1] 发送完整查询：'今天北京天气'")
    resp1 = requests.post(
        f"{BASE_URL}/api/v1/chat",
        json={"message": "今天北京天气", "session_id": SESSION_ID},
        timeout=300
    )
    print(f"  Status: {resp1.status_code}")
    data1 = resp1.json()
    content1 = data1.get("response", {}).get("text", "") if isinstance(data1, dict) else str(data1)
    print(f"  Response text (first 200 chars): {content1[:200]}")

    # A clarification response is typically short and contains "请问" etc.
    # A data response from the analyzer is a long structured analysis
    is_clarification_1 = any(word in content1 for word in ["请问您", "请提供", "请补充"]) and len(content1) < 200
    is_data_response_1 = len(content1) > 100 or any(word in content1 for word in ["数据", "天气", "温度", "结果", "概览", "指标"])
    print(f"  Is clarification: {is_clarification_1}")
    print(f"  Is data response: {is_data_response_1}")
    step1_pass = not is_clarification_1 and is_data_response_1
    print(f"  Step 1: {'PASS' if step1_pass else 'FAIL'}")

    # Step 2: Order query with complete info
    print("\n[Step 2] 发送另一完整查询：'最近7天订单量'")
    resp2 = requests.post(
        f"{BASE_URL}/api/v1/chat",
        json={"message": "最近7天订单量", "session_id": SESSION_ID},
        timeout=300
    )
    print(f"  Status: {resp2.status_code}")
    data2 = resp2.json()
    content2 = data2.get("response", {}).get("text", "") if isinstance(data2, dict) else str(data2)
    print(f"  Response text (first 200 chars): {content2[:200]}")

    is_clarification_2 = any(word in content2 for word in ["请问您", "请提供", "请补充"]) and len(content2) < 200
    is_data_response_2 = len(content2) > 100 or any(word in content2 for word in ["数据", "订单", "结果", "概览", "指标"])
    print(f"  Is clarification: {is_clarification_2}")
    print(f"  Is data response: {is_data_response_2}")
    step2_pass = not is_clarification_2 and is_data_response_2
    print(f"  Step 2: {'PASS' if step2_pass else 'FAIL'}")

    # Step 3: Check session history
    print("\n[Step 3] 检查sessions.json")
    try:
        with open("sessions.json", "r", encoding="utf-8") as f:
            sessions = json.load(f)
        if SESSION_ID in sessions:
            msg_count = len(sessions[SESSION_ID].get("messages", []))
            print(f"  Session messages: {msg_count}")
            step3_pass = msg_count >= 2
            print(f"  Step 3: {'PASS' if step3_pass else 'FAIL'}")
        else:
            print(f"  Session not found!")
            step3_pass = False
    except Exception as e:
        print(f"  Error reading sessions: {e}")
        step3_pass = False

    # Summary
    print("\n" + "=" * 60)
    all_pass = step1_pass and step2_pass and step3_pass
    print(f"VALIDATION CRITERIA:")
    print(f"  no_unnecessary_clarification: {'PASS' if step1_pass and step2_pass else 'FAIL'}")
    print(f"  direct_execution: {'PASS' if step1_pass and step2_pass else 'FAIL'}")
    print(f"  response_time_acceptable: PASS (both returned within timeout)")
    print(f"\nOVERALL: {'ALL PASS' if all_pass else 'SOME FAILED'}")
    print("=" * 60)

    return all_pass

if __name__ == "__main__":
    success = test_single_turn()
    sys.exit(0 if success else 1)
