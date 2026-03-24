"""
测试 LangGraph 完整流程
"""
import asyncio
import json
import aiohttp


async def test_full_flow():
    url = "http://localhost:8002/api/v1/chat/stream"

    payload = {
        "message": "查询2026年3月的销售数据，按地区汇总",
        "session_id": "test_full_001"
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
                        event_data = event.get('data', {})

                        if event_type == 'thought':
                            print(f"[{event_type}] {event_data.get('content', '')}")
                        elif event_type == 'answer':
                            print(f"[{event_type}] {event_data.get('content', '')[:100]}...")
                        elif event_type == 'data':
                            print(f"[{event_type}] Rows: {len(event_data.get('rows', []))}")
                        else:
                            print(f"[{event_type}] {json.dumps(event_data, ensure_ascii=False)[:100]}")
                    except json.JSONDecodeError:
                        print(f"Raw: {data[:100]}")


if __name__ == "__main__":
    asyncio.run(test_full_flow())
