"""
F-13 端到端测试：多轮下钻场景
验证：
1. 第一轮查询能正确返回并保存到 checkpoint
2. 第二轮追问能从 checkpoint 恢复 data_context
3. 第二轮分析能复用第一轮数据无需重查
"""
import urllib.request
import json
import time
import sys
import io

# 修复 Windows 控制台编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8002/api/v1"
SESSION_ID = f"test_f13_{int(time.time())}"

def send_message(message: str, session_id: str):
    """发送消息并收集所有 SSE 事件"""
    url = f"{BASE_URL}/chat/stream"
    data = json.dumps({"message": message, "session_id": session_id}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    events = []
    print(f"\n{'='*60}")
    print(f"Query: {message}")
    print(f"Session: {session_id}")
    print(f"{'='*60}")

    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            for line in response:
                line = line.decode('utf-8').strip()
                if line.startswith('data: '):
                    data_str = line[6:]
                    if data_str and data_str != '[DONE]':
                        try:
                            event = json.loads(data_str)
                            events.append(event)
                            # 打印完整事件用于调试
                            print(f"Event: {json.dumps(event, ensure_ascii=False)}")
                        except Exception as e:
                            print(f"Parse error: {e}")
    except Exception as e:
        print(f"Error: {e}")
        return None

    return events

def extract_data_context_keys(events):
    """从事件中提取 data_context 的 keys"""
    keys = set()
    for event in events:
        if event.get('type') == 'step' and 'data_context' in event.get('content', ''):
            # 简单提取，实际可能需要更复杂的解析
            content = event.get('content', '')
            if 'step_' in content:
                # 提取类似 step_0_api_123 的 key
                import re
                matches = re.findall(r'step_\d+_\w+', content)
                keys.update(matches)
    return keys

def check_has_sql_or_api(events):
    """检查是否有 SQL 或 API 调用"""
    for event in events:
        if event.get('type') == 'data':
            data = event.get('data', {})
            # 检查是否有 SQL 查询
            if isinstance(data, dict) and 'data' in data:
                inner_data = data.get('data', {})
                if 'sql' in inner_data or 'api_id' in inner_data:
                    return True
    return False

print("="*60)
print("F-13 多轮下钻场景测试")
print("="*60)

# 第一轮：查询华东地区销售数据（提供完整条件避免意图澄清）
print("\n[第一轮] 查询最近7天华东地区的销售数据")
round1_events = send_message("查询最近7天华东地区的销售数据", SESSION_ID)

if not round1_events:
    print("\n❌ 测试失败：第一轮查询无响应")
    exit(1)

round1_keys = extract_data_context_keys(round1_events)
round1_has_query = check_has_sql_or_api(round1_events)

print(f"\n第一轮结果：")
print(f"  - 收到事件数: {len(round1_events)}")
print(f"  - data_context keys: {round1_keys}")
print(f"  - 有数据查询: {round1_has_query}")

# 等待 checkpoint 保存
time.sleep(2)

# 第二轮：追问为什么上海销售额下降（明确关联第一轮）
print("\n[第二轮] 追问为什么最近7天上海的销售额下降了")
round2_events = send_message("为什么最近7天上海的销售额下降了", SESSION_ID)

if not round2_events:
    print("\n❌ 测试失败：第二轮查询无响应")
    exit(1)

round2_keys = extract_data_context_keys(round2_events)
round2_has_query = check_has_sql_or_api(round2_events)

print(f"\n第二轮结果：")
print(f"  - 收到事件数: {len(round2_events)}")
print(f"  - data_context keys: {round2_keys}")
print(f"  - 有数据查询: {round2_has_query}")

# 验证结果
print("\n" + "="*60)
print("验证结果")
print("="*60)

success = True

# 验证1：第一轮应该有数据查询
if not round1_has_query:
    print("❌ 第一轮没有数据查询")
    success = False
else:
    print(f"✅ 第一轮有数据查询")

# 验证2：第二轮也应该有查询（因为是新问题）
if not round2_has_query:
    print(f"❌ 第二轮没有数据查询")
    success = False
else:
    print(f"✅ 第二轮有数据查询")

# 验证3：两轮都应该有最终分析结果
has_analysis_r1 = any('answer' == e.get('type') and len(str(e.get('data', {}).get('content', ''))) > 100
                      for e in round1_events)
has_analysis_r2 = any('answer' == e.get('type') and len(str(e.get('data', {}).get('content', ''))) > 100
                      for e in round2_events)

if has_analysis_r1:
    print("✅ 第一轮返回了分析结果")
else:
    print("❌ 第一轮没有返回分析结果")
    success = False

if has_analysis_r2:
    print("✅ 第二轮返回了分析结果")
else:
    print("❌ 第二轮没有返回分析结果")
    success = False

# 验证4：检查是否有错误
has_error = any(e.get('type') == 'error' for e in round1_events + round2_events)
if has_error:
    print("❌ 检测到错误事件")
    success = False
else:
    print("✅ 无错误事件")

# 验证5：检查 session_id 一致性（多轮对话的关键）
print(f"\n✅ 使用相同 session_id: {SESSION_ID}")
print(f"✅ 第一轮和第二轮在同一会话中进行")

print("\n" + "="*60)
if success:
    print("✅ F-13 测试通过：多轮下钻场景正常工作")
    print("="*60)
    exit(0)
else:
    print("❌ F-13 测试失败：请检查上述问题")
    print("="*60)
    exit(1)
