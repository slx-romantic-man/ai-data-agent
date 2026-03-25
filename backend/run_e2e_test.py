"""
F-11 E2E Test: 简单查询场景
测试完整的 LangGraph 工作流
"""
import asyncio
import httpx
import json

async def test_e2e():
    url = "http://localhost:8000/api/v1/chat/stream"

    payload = {
        "conversation_id": "test-f11-e2e",
        "message": "查询最近七天的订单数量和订单总金额",
        "user_id": "test_user"
    }

    print("=" * 60)
    print("F-11 E2E Test: 简单查询场景")
    print("=" * 60)
    print(f"Query: {payload['message']}")
    print("-" * 60)

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", url, json=payload) as response:
            print(f"Status: {response.status_code}\n")

            if response.status_code != 200:
                print(f"Error: {await response.aread()}")
                return

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        print("\n" + "=" * 60)
                        print("Stream completed")
                        break

                    try:
                        data = json.loads(data_str)
                        event_type = data.get("type", "")

                        if event_type == "node_start":
                            node = data.get("node", "")
                            print(f"\n[Node Start] {node}")

                        elif event_type == "node_end":
                            node = data.get("node", "")
                            print(f"[Node End] {node}")

                        elif event_type == "content":
                            content = data.get("content", "")
                            if content:
                                print(content, end="", flush=True)

                        elif event_type == "error":
                            print(f"\n[Error] {data.get('content', '')}")

                        elif event_type == "final_result":
                            print(f"\n\n[Final Result]")
                            result = data.get("result", {})
                            print(json.dumps(result, ensure_ascii=False, indent=2))

                    except json.JSONDecodeError:
                        pass

if __name__ == "__main__":
    print("\n请确保后端服务已启动: python -m uvicorn app.main:app --reload\n")
    asyncio.run(test_e2e())
