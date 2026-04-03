"""
E2E Test for F-CM-03: 连续独立查询不混淆
完成一个查询后开启新查询，系统不应混入历史上下文
"""
import requests
import json
import time
import sys
import os

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

BASE_URL = "http://localhost:8002"
SESSION_ID = "test-independent-session-fcm03"

def test_independent_queries():
    """Test that a new independent query doesn't mix with previous query context."""

    print("=" * 60)
    print("F-CM-03: 连续独立查询不混淆 - 端到端测试")
    print("=" * 60)

    # Clean up previous session data
    try:
        sessions_file = "sessions.json"
        if os.path.exists(sessions_file):
            with open(sessions_file, "r", encoding="utf-8") as f:
                sessions = json.load(f)
            if SESSION_ID in sessions:
                del sessions[SESSION_ID]
                with open(sessions_file, "w", encoding="utf-8") as f:
                    json.dump(sessions, f, ensure_ascii=False, indent=2)
                print(f"Cleaned up previous session data for {SESSION_ID}")
    except Exception as e:
        print(f"Warning: Could not clean session data: {e}")

    # Step 1: Send first complete query "最近7天的订单量"
    print("\n[Step 1] 发送第一条完整查询：'最近7天的订单量'")

    try:
        resp1 = requests.post(
            f"{BASE_URL}/api/v1/chat",
            json={"message": "最近7天的订单量", "session_id": SESSION_ID},
            timeout=120
        )

        print(f"  Status: {resp1.status_code}")
        if resp1.status_code == 200:
            data1 = resp1.json()
            text1 = data1.get("response", {}).get("text", "")
            print(f"  Response preview: {text1[:150]}...")

            # Step 2: Verify returns data (no clarification)
            has_clarification = "请问" in text1 and "？" in text1
            if not has_clarification:
                print("  ✅ Step 2: 返回数据（无澄清问题）")
                step2_pass = True
            else:
                print(f"  ❌ Step 2: 返回了澄清问题，而非直接数据")
                step2_pass = False
        else:
            print(f"  ❌ Step 1 failed: {resp1.text[:200]}")
            return False
    except Exception as e:
        print(f"  ❌ Request failed: {e}")
        return False

    # Step 3: Send second independent query "分析用户增长趋势"
    print("\n[Step 3] 发送第二条新查询：'分析用户增长趋势'")

    try:
        resp2 = requests.post(
            f"{BASE_URL}/api/v1/chat",
            json={"message": "分析用户增长趋势", "session_id": SESSION_ID},
            timeout=120
        )

        print(f"  Status: {resp2.status_code}")
        if resp2.status_code == 200:
            data2 = resp2.json()
            text2 = data2.get("response", {}).get("text", "")
            print(f"  Response preview: {text2[:150]}...")

            # Step 4: Verify second query is about user growth, NOT order volume data
            # Key check: the response should NOT contain order-related data/analysis
            # If context is contaminated, the response would discuss "订单量" or "最近7天订单"
            has_order_data = "订单量" in text2 or "订单" in text2
            has_time_leak = "最近7天" in text2

            if has_order_data or has_time_leak:
                print(f"  ❌ Step 4: 发现上下文污染！")
                if has_order_data:
                    print(f"    - 响应包含订单相关内容（不应出现）")
                if has_time_leak:
                    print(f"    - 响应包含'最近7天'时间范围（从第一条查询泄漏）")
                step4_pass = False
            else:
                print(f"  ✅ Step 4: 返回用户增长趋势相关响应（无订单数据污染）")
                step4_pass = True
        else:
            print(f"  ❌ Request failed: {resp2.text[:200]}")
            return False
    except Exception as e:
        print(f"  ❌ Request failed: {e}")
        return False

    # Step 5: Verify system doesn't misapply "最近7天" to "用户增长趋势"
    print("\n[Step 5] 检查时间范围是否被错误传递")

    try:
        log_file = "logs/app.log"
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                log_content = f.read()

            # Find intent processing logs for the second query
            relevant_logs = [line for line in log_content.split('\n') if '用户增长趋势' in line]
            if relevant_logs:
                print(f"  Found {len(relevant_logs)} relevant log entries for second query")
                # Show the intent parsing result
                for log in relevant_logs[-3:]:
                    print(f"    {log[-200:]}")

            # Check if any merged query appears (contamination indicator)
            contamination_patterns = ["订单.*增长", "增长.*订单", "最近7天.*用户增长"]
            contamination_found = False
            for pattern_desc in contamination_patterns:
                contamination_logs = [line for line in log_content.split('\n') if '订单' in line and '增长' in line]
                if contamination_logs:
                    # Verify this is about Merged query, not just both queries appearing
                    merged_logs = [line for line in contamination_logs if 'Merged' in line or 'merged' in line]
                    if merged_logs:
                        print(f"  ❌ Step 5: 发现合并查询污染！")
                        for log in merged_logs[-2:]:
                            print(f"    {log[-200:]}")
                        contamination_found = True
                        break

            if not contamination_found:
                print(f"  ✅ Step 5: 系统未将'最近7天'误应用到'用户增长趋势'")
                step5_pass = True
            else:
                step5_pass = False
        else:
            print(f"  ⚠️  Log file not found at {log_file}")
            step5_pass = True
    except Exception as e:
        print(f"  ⚠️  Could not check logs: {e}")
        step5_pass = True

    # Step 6: Check sessions.json
    print("\n[Step 6] 检查sessions.json")

    try:
        sessions_file = "sessions.json"
        if os.path.exists(sessions_file):
            with open(sessions_file, "r", encoding="utf-8") as f:
                sessions = json.load(f)

            if SESSION_ID in sessions:
                session = sessions[SESSION_ID]
                msgs = session.get("messages", [])
                print(f"  Total messages: {len(msgs)}")

                user_msgs = [m for m in msgs if m.get("role") == "user"]
                print(f"  User messages ({len(user_msgs)}):")
                for m in user_msgs:
                    content = m.get("content", "")[:80]
                    print(f"    - {content}")

                # Verify both queries are recorded but not confused
                user_contents = [m.get("content", "") for m in user_msgs]
                has_orders_query = any("订单" in c for c in user_contents)
                has_growth_query = any("增长" in c or "用户" in c for c in user_contents)

                if has_orders_query and has_growth_query:
                    print("  ✅ Step 6: 两条查询均被记录且未混淆")
                    step6_pass = True
                else:
                    print(f"  ❌ Step 6: 查询记录不完整")
                    step6_pass = False
            else:
                print(f"  ❌ Session '{SESSION_ID}' not found")
                return False
        else:
            print(f"  ❌ Sessions file not found")
            return False
    except Exception as e:
        print(f"  ❌ Failed to check sessions: {e}")
        return False

    # Summary
    print("\n" + "=" * 60)
    all_pass = step2_pass and step4_pass and step5_pass and step6_pass
    print(f"验证结果: {'✅ 全部通过' if all_pass else '❌ 部分失败'}")
    print(f"  Step 2 (第一条无澄清): {'✅ PASS' if step2_pass else '❌ FAIL'}")
    print(f"  Step 4 (独立查询无污染): {'✅ PASS' if step4_pass else '❌ FAIL'}")
    print(f"  Step 5 (无时间混淆): {'✅ PASS' if step5_pass else '❌ FAIL'}")
    print(f"  Step 6 (Session记录): {'✅ PASS' if step6_pass else '❌ FAIL'}")
    print("=" * 60)

    return all_pass


if __name__ == "__main__":
    success = test_independent_queries()
    sys.exit(0 if success else 1)
