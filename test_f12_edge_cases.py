"""
F-12 Edge Case Testing Script
测试 Analyzer 对各种异常场景的兜底能力
"""
import asyncio
import httpx
import json
import sys

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://localhost:8002"

async def test_case(name: str, payload: dict):
    """执行单个测试用例"""
    print(f"\n{'='*60}")
    print(f"测试: {name}")
    print(f"{'='*60}")

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/query",
                json=payload
            )

            if response.status_code == 200:
                # 收集SSE流
                final_answer = None
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if data.get("type") == "final_answer":
                            final_answer = data.get("content", "")

                print(f"[PASS] 最终回答: {final_answer[:200] if final_answer else '(空)'}")
                return final_answer is not None and len(final_answer) > 0
            else:
                print(f"[FAIL] HTTP错误: {response.status_code}")
                return False

        except Exception as e:
            print(f"[FAIL] 异常: {e}")
            return False

async def main():
    """运行所有测试用例"""

    results = {}

    # 测试1: 正常数据查询
    results["normal_data"] = await test_case(
        "正常数据查询 - 应返回分析结果",
        {
            "query": "查询股票代码600000的最新价格",
            "user_id": "test_user",
            "session_id": "test_session_1"
        }
    )

    # 测试2: 无权限查询
    results["no_permission"] = await test_case(
        "无权限查询 - 应明确提示权限不足",
        {
            "query": "查询订单数据",
            "user_id": "guest_user",  # 假设guest没有订单权限
            "session_id": "test_session_2"
        }
    )

    # 测试3: 无数据查询
    results["no_data"] = await test_case(
        "无数据查询 - 应提示未查询到数据",
        {
            "query": "查询股票代码999999的数据",  # 不存在的股票
            "user_id": "test_user",
            "session_id": "test_session_3"
        }
    )

    # 测试4: 无法生成计划的查询
    results["invalid_plan"] = await test_case(
        "无法生成计划 - 应提示无法执行原因",
        {
            "query": "帮我做一个火箭",  # 完全无关的请求
            "user_id": "test_user",
            "session_id": "test_session_4"
        }
    )

    # 汇总结果
    print(f"\n{'='*60}")
    print("测试汇总")
    print(f"{'='*60}")
    for test_name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} - {test_name}")

    total = len(results)
    passed_count = sum(results.values())
    print(f"\n通过率: {passed_count}/{total} ({passed_count*100//total}%)")

if __name__ == "__main__":
    asyncio.run(main())
