"""F-CM-07 E2E 验证：Stream Chat历史格式清洗"""
import json
import os
import time
import http.client

BASE_HOST = "localhost"
BASE_PORT = 8002
SESSION_ID = "test-f-cm-07-stream"

print("=" * 60)
print("F-CM-07: Stream Chat历史格式清洗 - E2E验证")
print("=" * 60)

# Step 1: 验证代码清洗逻辑
print("\n[Step 1] 验证stream_chat代码包含格式清洗逻辑...")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(SCRIPT_DIR, "app/api/v1/chat.py"), "r", encoding="utf-8") as f:
    content = f.read()

has_format_cleaning = "Format conversation history for LangGraph" in content and "formatted_history" in content
print(f"  格式清洗代码存在: {'PASS' if has_format_cleaning else 'FAIL'}")

has_type_preservation = '"type" in msg' in content
print(f"  type字段保留逻辑: {'PASS' if has_type_preservation else 'FAIL'}")

# Check stream_chat uses formatted_history (not raw conversation_history)
# Find the stream_chat section and verify it uses formatted_history
stream_section = content[content.find("async def stream_chat"):]
uses_formatted = "formatted_history" in stream_section[:2000]
uses_initial = '"messages": formatted_history' in stream_section[:2000]
print(f"  stream_chat使用formatted_history: {'PASS' if uses_formatted and uses_initial else 'FAIL'}")

# Step 2: 使用http.client测试流式接口（更好的流式处理）
def stream_sse(path, body, timeout=120):
    """Send POST request and collect SSE events until 'done' or timeout."""
    conn = http.client.HTTPConnection(BASE_HOST, BASE_PORT, timeout=timeout)
    headers = {"Content-Type": "application/json"}
    conn.request("POST", path, body=json.dumps(body), headers=headers)
    resp = conn.getresponse()
    events = []
    start = time.time()
    while time.time() - start < timeout:
        line = resp.readline().decode("utf-8").strip()
        if not line:
            if resp.isclosed():
                break
            continue
        if line.startswith("data: "):
            try:
                event = json.loads(line[6:])
                events.append(event)
                if event.get("type") == "done":
                    break
            except json.JSONDecodeError:
                pass
    conn.close()
    return resp.status, events

# Clean old session
try:
    with open(os.path.join(SCRIPT_DIR, "sessions.json"), "r", encoding="utf-8") as f:
        sessions = json.load(f)
    sessions.pop(SESSION_ID, None)
    with open(os.path.join(SCRIPT_DIR, "sessions.json"), "w", encoding="utf-8") as f:
        json.dump(sessions, f, indent=2, ensure_ascii=False)
except:
    pass

# Step 2: First query - should get clarification
print("\n[Step 2] 发送第一条流式查询...")
status, events = stream_sse(
    "/api/v1/chat/stream",
    {"message": "分析苹果美股股价变化", "session_id": SESSION_ID},
    timeout=90
)
print(f"  Status: {status}")

first_clarification = False
for e in events:
    if e.get("type") == "answer":
        content_text = e.get("data", {}).get("content", "")
        print(f"  Answer: {content_text[:80]}...")
        if "请问" in content_text or "时间范围" in content_text:
            first_clarification = True

print(f"  事件总数: {len(events)}")
print(f"  包含澄清问题: {'PASS' if first_clarification else 'FAIL'}")

# Step 3: Second query - should get data (not ask again)
print("\n[Step 3] 发送第二条流式查询（补充信息）...")
status2, events2 = stream_sse(
    "/api/v1/chat/stream",
    {"message": "近期的", "session_id": SESSION_ID},
    timeout=90
)
print(f"  Status: {status2}")

got_data = False
asked_again = False
for e in events2:
    if e.get("type") == "answer":
        content_text = e.get("data", {}).get("content", "")
        print(f"  Answer: {content_text[:80]}...")
        if "请问" in content_text:
            asked_again = True
        if any(kw in content_text for kw in ["股价", "数据", "分析", "趋势", "近期", "时间"]):
            got_data = True

print(f"  事件总数: {len(events2)}")
print(f"  返回数据而非再次询问: {'PASS' if got_data and not asked_again else 'FAIL'}")

# Step 4: Check sessions.json format
print("\n[Step 4] 检查sessions.json格式一致性...")
try:
    with open(os.path.join(SCRIPT_DIR, "sessions.json"), "r", encoding="utf-8") as f:
        sessions = json.load(f)
    session = sessions.get(SESSION_ID, {})
    messages = session.get("messages", [])
    print(f"  Session消息数: {len(messages)}")

    has_timestamp = any("timestamp" in msg for msg in messages)
    has_role = all("role" in msg for msg in messages)
    has_content = all("content" in msg for msg in messages)
    # Check that loaded history (formatted_history) does NOT contain timestamp
    has_type_in_session = any("type" in msg for msg in messages)
    print(f"  消息格式正确(role+content+timestamp): {'PASS' if has_role and has_content and has_timestamp else 'FAIL'}")
    print(f"  消息数>=4 (2轮对话): {'PASS' if len(messages) >= 4 else 'FAIL'}")
    print(f"  包含type字段(用于澄清检测): {'PASS' if has_type_in_session else 'FAIL'}")
except Exception as e:
    print(f"  FAIL: {e}")

# Step 5: 验证stream_chat保存时保留type字段
print("\n[Step 5] 验证stream_chat保存逻辑保留type字段...")
# The first assistant message should have type=clarification
if messages:
    first_assistant = None
    for msg in messages:
        if msg.get("role") == "assistant":
            first_assistant = msg
            break
    has_type = first_assistant and first_assistant.get("type") == "clarification"
    print(f"  第一条assistant消息type=clarification: {'PASS' if has_type else 'FAIL'}")

print("\n" + "=" * 60)
print("验证完成")
print("=" * 60)
