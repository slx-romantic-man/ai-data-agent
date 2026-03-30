import asyncio
import sys
sys.path.insert(0, 'backend')

from app.config.llm_config import get_llm

async def test():
    llm = get_llm()
    print('Provider:', llm.__class__.__name__)
    messages = [{'role': 'user', 'content': '1+1=?'}]
    response = await llm.chat(messages)
    print('Response:', response[:100])

asyncio.run(test())
