"""
F-24: 三个外部 API 的端到端复杂问题测试
为股票、天气、IP 三个 API 各设计 3 条不同表述的自然语言问题
验证 Agent 的鲁棒性和最终回答质量
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import json
import time

BASE_URL = "http://127.0.0.1:8002"

# 测试问题集
TEST_CASES = {
    "stock_api": [
        {"question": "苹果股价", "expected_keywords": ["AAPL", "股价", "美元", "$"]},
        {"question": "AAPL今天涨了吗", "expected_keywords": ["AAPL", "涨", "跌"]},
        {"question": "查询Apple股票", "expected_keywords": ["AAPL", "股票"]},
    ],
    "weather_api": [
        {"question": "上海天气", "expected_keywords": ["上海", "温度", "天气", "°C"]},
        {"question": "北京今天冷吗", "expected_keywords": ["北京", "温度", "°C"]},
        {"question": "深圳气温多少", "expected_keywords": ["深圳", "温度", "气温", "°C"]},
    ],
    "ip_api": [
        {"question": "查IP位置8.8.8.8", "expected_keywords": ["8.8.8.8", "美国", "US"]},
        {"question": "这个IP在哪114.114.114.114", "expected_keywords": ["114.114.114.114", "中国", "CN"]},
        {"question": "定位IP地址1.1.1.1", "expected_keywords": ["1.1.1.1"]},
    ],
}

def test_question(session_id: str, question: str, expected_keywords: list) -> dict:
    """测试单个问题"""
    print(f"\n{'='*60}")
    print(f"📝 问题: {question}")
    print(f"🎯 期望关键词: {expected_keywords}")

    # 发送问题（使用admin用户，拥有所有API权限）
    # chat端点是同步的，会等待Agent完成后返回
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/chat",
            json={
                "session_id": session_id,
                "message": question,
                "user_id": "admin"
            },
            timeout=60  # 60秒超时
        )
    except requests.exceptions.Timeout:
        print("❌ 请求超时（60秒）")
        return {"success": False, "error": "timeout"}
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return {"success": False, "error": str(e)}

    if response.status_code != 200:
        print(f"❌ 请求失败: {response.status_code}")
        return {"success": False, "error": "request_failed"}

    # 从同步响应中获取答案
    data = response.json()
    final_answer = data.get("response", {}).get("text", "")

    if not final_answer:
        print("❌ 未找到最终回答")
        return {"success": False, "error": "no_final_answer"}

    print(f"✅ 最终回答: {final_answer[:200]}...")

    # 检查关键词
    matched_keywords = [kw for kw in expected_keywords if kw.lower() in final_answer.lower()]

    if matched_keywords:
        print(f"✅ 匹配关键词: {matched_keywords}")
        return {"success": True, "answer": final_answer, "matched": matched_keywords}
    else:
        print(f"⚠️  未匹配任何关键词")
        return {"success": True, "answer": final_answer, "matched": []}

def main():
    print("🚀 F-24: 三个外部 API 端到端复杂问题测试")
    print("="*60)

    results = {}

    for api_name, test_cases in TEST_CASES.items():
        print(f"\n\n{'#'*60}")
        print(f"# 测试 API: {api_name}")
        print(f"{'#'*60}")

        api_results = []

        for idx, test_case in enumerate(test_cases, 1):
            session_id = f"f24_{api_name}_{idx}_{int(time.time())}"
            result = test_question(
                session_id=session_id,
                question=test_case["question"],
                expected_keywords=test_case["expected_keywords"]
            )
            api_results.append({
                "question": test_case["question"],
                "result": result
            })
            time.sleep(1)  # 减少测试间隔

        results[api_name] = api_results

    # 生成测试报告
    print("\n\n" + "="*60)
    print("📊 测试报告")
    print("="*60)

    total_tests = 0
    passed_tests = 0

    for api_name, api_results in results.items():
        print(f"\n{api_name}:")
        for test in api_results:
            total_tests += 1
            status = "✅" if test["result"]["success"] else "❌"
            matched = len(test["result"].get("matched", []))
            if test["result"]["success"] and matched > 0:
                passed_tests += 1
            print(f"  {status} {test['question']} (匹配 {matched} 个关键词)")

    print(f"\n总计: {passed_tests}/{total_tests} 通过")

    if passed_tests == total_tests:
        print("\n🎉 F-24 测试全部通过!")
        return True
    else:
        print(f"\n⚠️  F-24 测试未完全通过 ({passed_tests}/{total_tests})")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
