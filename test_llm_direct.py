"""
直接测试LLM连接
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.config.llm_config import get_llm


async def test_llm():
    llm = get_llm()

    print("Testing LLM connection...")
    try:
        response = await llm.chat([
            {"role": "user", "content": "Hello, respond with 'OK'"}
        ])
        print(f"[SUCCESS] LLM Response: {response}")
        return True
    except Exception as e:
        print(f"[FAIL] LLM Error: {e}")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_llm())
    sys.exit(0 if result else 1)
