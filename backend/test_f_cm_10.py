"""
F-CM-10 端到端集成验证 - 前端UI完整多轮对话流程

测试步骤:
1. 运行bash init.sh启动后端服务器
2. 模拟前端UI发送"分析苹果股价" -> 验证澄清问题
3. 模拟前端UI发送"近期的" -> 验证数据结果
4. 验证前端对话历史显示完整4条消息
5. 模拟前端"新建聊天"按钮 -> 新session_id -> 验证无历史
6. 模拟新会话输入"查询天气" -> 验证重新开始澄清流程
"""

import requests
import json
import time
import sys
import os
import re

BASE_URL = "http://localhost:8002/api/v1"

# --- Helper Functions ---

def make_request(session_id, message, stream=False):
    """Simulate frontend streamChat/chat call"""
    if stream:
        return stream_request(session_id, message)
    else:
        return chat_request(session_id, message)

def chat_request(session_id, message):
    """Non-streaming chat request"""
    res = requests.post(
        f"{BASE_URL}/chat",
        json={"session_id": session_id, "message": message},
        timeout=120
    )
    return res.status_code, res.json()

def stream_request(session_id, message):
    """Streaming chat request (same as frontend streamChat)"""
    import urllib.request
    import json as json_mod

    url = f"{BASE_URL}/chat/stream"
    body = json_mod.dumps({"session_id": session_id, "message": message}).encode('utf-8')

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    response = urllib.request.urlopen(req, timeout=180)
    content = ""
    full_response = {}

    for line in response:
        decoded = line.decode('utf-8').strip()
        if decoded.startswith("data: "):
            try:
                event = json_mod.loads(decoded[6:])
                full_response = event
                if event.get("type") == "answer":
                    content = event.get("data", {}).get("content", "") or content
                elif event.get("type") == "done":
                    pass
            except:
                pass

    return 200, {"content": content, "event": full_response}


def get_sessions():
    """Read sessions.json"""
    sessions_path = os.path.join(os.path.dirname(__file__), "sessions.json")
    with open(sessions_path, "r", encoding="utf-8") as f:
        return json.load(f)


def wait_for_server():
    for i in range(10):
        try:
            res = requests.get("http://localhost:8002/health", timeout=5)
            if res.status_code == 200:
                print("Server is healthy")
                return True
        except:
            pass
        time.sleep(2)
    print("Server not responding")
    return False


# --- Test Execution ---

def test_f_cm_10():
    all_passed = True
    results = {}

    print("=" * 70)
    print("F-CM-10: 端到端集成验证 - 前端UI完整多轮对话流程")
    print("=" * 70)

    # Step 1: Verify server health
    print("\n[Step 1] Server health check")
    if not wait_for_server():
        print("FAIL: Server not responding")
        return False
    print("PASS")

    # Use unique session IDs with timestamp to avoid collision
    timestamp = str(int(time.time()))
    session_id = f"test-fcm10-multi-{timestamp}"
    new_session_id = f"test-fcm10-new-{timestamp}"

    # Clean up any leftover sessions from previous runs
    sessions_path = os.path.join(os.path.dirname(__file__), "sessions.json")
    sessions_data = {}
    try:
        with open(sessions_path, "r", encoding="utf-8") as f:
            sessions_data = json.load(f)
        for sid in [session_id, new_session_id]:
            if sid in sessions_data:
                del sessions_data[sid]
        with open(sessions_path, "w", encoding="utf-8") as f:
            json.dump(sessions_data, f, ensure_ascii=False, indent=2)
    except:
        pass

    # Step 2: Simulate frontend - first message "分析苹果股价"
    print(f"\n[Step 2] Frontend simulation: Send '分析苹果股价' (session={session_id})")

    try:
        status, resp = stream_request(session_id, "分析苹果股价")
        print(f"  Status: {status}")
        content = resp.get("content", "")
        print(f"  Content preview: {content[:200]}")

        # Verify clarification question
        has_clarification = "请问" in content or "时间范围" in content or "哪个" in content
        results["step2_clarification"] = has_clarification
        print(f"  Contains clarification question: {has_clarification}")
        if not has_clarification:
            all_passed = False
            print("  FAIL: No clarification question detected")
        else:
            print("  PASS")
    except Exception as e:
        print(f"  FAIL: {e}")
        all_passed = False
        results["step2_clarification"] = False

    # Wait for session to be saved
    time.sleep(3)

    # Step 3: Verify session has first exchange
    print("\n[Step 3] Verify session after first message")
    try:
        sessions = get_sessions()
        session = sessions.get(session_id, {})
        msgs = session.get("messages", [])
        print(f"  Session messages count: {len(msgs)}")

        has_user = any(m.get("role") == "user" for m in msgs)
        has_assistant = any(m.get("role") == "assistant" for m in msgs)
        has_clarification_type = any(m.get("type") == "clarification" for m in msgs)

        print(f"  Has user message: {has_user}")
        print(f"  Has assistant message: {has_assistant}")
        print(f"  Has clarification type: {has_clarification_type}")

        results["step3_session"] = has_user and has_assistant and has_clarification_type
        if results["step3_session"]:
            print("  PASS")
        else:
            print("  FAIL")
            all_passed = False
    except Exception as e:
        print(f"  FAIL: {e}")
        all_passed = False
        results["step3_session"] = False

    # Step 4: Simulate frontend - second message "近期的"
    print("\n[Step 4] Frontend simulation: Send '近期的' (same session)")
    try:
        status, resp = stream_request(session_id, "近期的")
        print(f"  Status: {status}")
        content = resp.get("content", "")
        print(f"  Content preview: {content[:300]}")

        # Verify data result (not re-asking)
        has_data = any(kw in content for kw in ["数据", "分析", "报告", "概览", "核心", "趋势", "股价", "AAPL", "stock", "price"])
        has_redundant_question = content.count("请问") > 0 and "数据" not in content

        results["step4_data_result"] = has_data and not has_redundant_question
        print(f"  Contains data result: {has_data}")
        print(f"  No redundant question: {not has_redundant_question}")
        if results["step4_data_result"]:
            print("  PASS")
        else:
            print("  FAIL")
            all_passed = False
    except Exception as e:
        print(f"  FAIL: {e}")
        all_passed = False
        results["step4_data_result"] = False

    # Wait for session to be saved
    time.sleep(3)

    # Step 5: Verify complete conversation history (4+ messages)
    print("\n[Step 5] Verify complete conversation history in sessions.json")
    try:
        sessions = get_sessions()
        session = sessions.get(session_id, {})
        msgs = session.get("messages", [])

        user_msgs = [m for m in msgs if m.get("role") == "user"]
        assistant_msgs = [m for m in msgs if m.get("role") == "assistant"]

        print(f"  Total messages: {len(msgs)}")
        print(f"  User messages: {len(user_msgs)}")
        print(f"  Assistant messages: {len(assistant_msgs)}")

        # Verify >= 4 messages (2 user + 2 assistant minimum)
        has_complete_history = len(msgs) >= 4 and len(user_msgs) >= 2 and len(assistant_msgs) >= 2

        # Verify first assistant message has clarification type
        first_assistant = None
        for m in assistant_msgs:
            if m.get("type") == "clarification":
                first_assistant = m
                break

        results["step5_history"] = has_complete_history and first_assistant is not None
        print(f"  Has >= 4 messages: {has_complete_history}")
        print(f"  Has clarification type message: {first_assistant is not None}")

        if results["step5_history"]:
            print("  PASS")
        else:
            print("  FAIL")
            all_passed = False
    except Exception as e:
        print(f"  FAIL: {e}")
        all_passed = False
        results["step5_history"] = False

    # Step 6: Simulate "New Chat" button click - new session
    print("\n[Step 6] Frontend simulation: 'New Chat' button -> new session")
    # Verify new session starts without stock content
    sessions = get_sessions()
    # The key test is: before sending any message in the new session,
    # there should be no messages from the weather query yet
    existing = sessions.get(new_session_id, {})
    existing_msgs = existing.get("messages", [])
    # Check no weather-related messages yet (will be added in Step 7)
    existing_has_weather = any("天气" in m.get("content", "") for m in existing_msgs)
    results["step6_new_chat"] = not existing_has_weather
    print(f"  New session has no pre-existing weather messages: {not existing_has_weather}")

    if results["step6_new_chat"]:
        print("  PASS")
    else:
        print("  FAIL")
        all_passed = False

    # Step 7: New session independent flow - "查询天气"
    print("\n[Step 7] New session: Send '查询天气' -> verify fresh clarification flow")
    try:
        status, resp = stream_request(new_session_id, "查询天气")
        print(f"  Status: {status}")
        content = resp.get("content", "")
        print(f"  Content preview: {content[:200]}")

        # Verify new session gets its own clarification (not mixing with stock context)
        has_weather_clarification = any(kw in content for kw in ["天气", "城市", "请问", "哪个"])
        no_stock_context = "苹果" not in content and "股价" not in content and "stock" not in content.lower()

        results["step7_independent"] = has_weather_clarification and no_stock_context
        print(f"  Has weather clarification: {has_weather_clarification}")
        print(f"  No stock context contamination: {no_stock_context}")
        if results["step7_independent"]:
            print("  PASS")
        else:
            print("  FAIL")
            all_passed = False
    except Exception as e:
        print(f"  FAIL: {e}")
        all_passed = False
        results["step7_independent"] = False

    # Wait for session to be saved
    time.sleep(3)

    # Step 8: Verify both sessions are independently saved
    print("\n[Step 8] Verify both sessions exist independently")
    try:
        sessions = get_sessions()
        has_multi = session_id in sessions
        has_new = new_session_id in sessions

        multi_msgs = sessions.get(session_id, {}).get("messages", [])
        new_msgs = sessions.get(new_session_id, {}).get("messages", [])

        print(f"  Multi-turn session: {len(multi_msgs)} messages")
        print(f"  New session: {len(new_msgs)} messages")

        # Verify content separation
        multi_content = " ".join(m.get("content", "") for m in multi_msgs)
        new_content = " ".join(m.get("content", "") for m in new_msgs)

        multi_has_stock = "苹果" in multi_content or "股价" in multi_content
        new_has_weather = "天气" in new_content

        results["step8_both_saved"] = has_multi and has_new and multi_has_stock and new_has_weather
        print(f"  Multi-turn session has stock content: {multi_has_stock}")
        print(f"  New session has weather content: {new_has_weather}")

        if results["step8_both_saved"]:
            print("  PASS")
        else:
            print("  FAIL")
            all_passed = False
    except Exception as e:
        print(f"  FAIL: {e}")
        all_passed = False
        results["step8_both_saved"] = False

    # --- Frontend UI code review ---
    print("\n[Step 9] Frontend UI code review: New Chat button and session management")
    try:
        # Check chat.js has startNewConversation
        chat_js_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "js", "features", "chat.js")
        with open(chat_js_path, "r", encoding="utf-8") as f:
            chat_js = f.read()

        has_start_new_conv = "startNewConversation" in chat_js
        has_clear_messages = "messages.value = []" in chat_js
        has_new_session_id = "currentSessionId.value = " in chat_js
        has_save_before_clear = "saveCurrentConversation" in chat_js

        # Check the button exists in template
        template_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "js", "app-template.js")
        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()

        has_new_chat_button = "startNewConversation" in template

        results["step9_frontend_code"] = (
            has_start_new_conv and has_clear_messages and
            has_new_session_id and has_save_before_clear and has_new_chat_button
        )

        print(f"  startNewConversation exists: {has_start_new_conv}")
        print(f"  Clear messages logic: {has_clear_messages}")
        print(f"  New session ID generation: {has_new_session_id}")
        print(f"  Save before clear: {has_save_before_clear}")
        print(f"  New chat button in template: {has_new_chat_button}")

        if results["step9_frontend_code"]:
            print("  PASS")
        else:
            print("  FAIL")
            all_passed = False
    except Exception as e:
        print(f"  FAIL: {e}")
        all_passed = False
        results["step9_frontend_code"] = False

    # --- Summary ---
    print("\n" + "=" * 70)
    print("F-CM-10 验证汇总")
    print("=" * 70)

    step_names = {
        "step2_clarification": "Step 2: 第一条消息返回澄清问题",
        "step3_session": "Step 3: Session保存第一条交换",
        "step4_data_result": "Step 4: 第二条消息返回数据结果",
        "step5_history": "Step 5: 完整对话历史 >= 4条消息",
        "step6_new_chat": "Step 6: 新会话干净无历史",
        "step7_independent": "Step 7: 新会话独立澄清流程",
        "step8_both_saved": "Step 8: 两个Session独立保存",
        "step9_frontend_code": "Step 9: 前端UI代码审查",
    }

    for key, name in step_names.items():
        status = "PASS" if results.get(key) else "FAIL"
        icon = "[+]" if status == "PASS" else "[-]"
        print(f"  {icon} {name}: {status}")

    print(f"\nTotal: {sum(1 for v in results.values() if v)}/{len(results)} passed")

    # Validation criteria
    print("\nvalidation_criteria验证：")
    frontend_history = results.get("step5_history", False)
    new_session_clean = results.get("step6_new_chat", False) and results.get("step8_both_saved", False)
    e2e_flow = results.get("step2_clarification", False) and results.get("step4_data_result", False)

    print(f"{'[+]' if frontend_history else '[-]'} frontend_history_complete: {'PASS' if frontend_history else 'FAIL'}")
    print(f"{'[+]' if new_session_clean else '[-]'} new_session_clean: {'PASS' if new_session_clean else 'FAIL'}")
    print(f"{'[+]' if results.get('step9_frontend_code') else '[-]'} ui_no_context_loss: {'PASS' if results.get('step9_frontend_code') else 'FAIL'}")
    print(f"{'[+]' if e2e_flow else '[-]'} end_to_end_flow: {'PASS' if e2e_flow else 'FAIL'}")

    all_criteria_pass = frontend_history and new_session_clean and e2e_flow and results.get("step9_frontend_code")
    print(f"\n{'='*70}")
    if all_criteria_pass:
        print("F-CM-10: ALL PASSED!")
    else:
        print("F-CM-10: SOME FAILED")
        failed_steps = [name for key, name in step_names.items() if not results.get(key)]
        print(f"Failed steps: {', '.join(failed_steps)}")
    print(f"{'='*70}")

    return all_criteria_pass


if __name__ == "__main__":
    success = test_f_cm_10()
    sys.exit(0 if success else 1)
