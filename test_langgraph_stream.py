"""
测试 LangGraph 流式输出
"""
import asyncio
import json
import aiohttp


async def test_stream():
    url = "http://localhost:8002/api/v1/chat/stream"

    payload = {
        "message": "查询销售数据",
        "session_id": "test_session_001"
    }

    headers = {
        "Content-Type": "application/json",
        "X-User-ID": "test_user"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            print(f"Status: {response.status}")
            print("Streaming events:")
            print("-" * 50)

            async for line in response.content:
                line = line.decode('utf-8').strip()
                if line.startswith('data: '):
                    data = line[6:]
                    try:
                        event = json.loads(data)
                        event_type = event.get('type')
                        print(f"[{event_type}] {json.dumps(event.get('data', {}), ensure_ascii=False)}")
                    except json.JSONDecodeError:
                        print(f"Raw: {data}")


if __name__ == "__main__":
    asyncio.run(test_stream())
