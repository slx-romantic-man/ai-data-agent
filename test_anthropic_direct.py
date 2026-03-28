"""
Test Anthropic client directly
"""
import asyncio


async def test_anthropic():
    try:
        import anthropic
        import os

        api_key = "sk-cp-b9-yITc2R_pY9ckBiaRro13OUaABhnPov_zs4Xv5eX-lfokaKyVVv1ZdOBO4mWh8ObE4nrONzVAFbYOKd9tKENZNbLnJkaY1Bs67PTHHXK1_rfYapcSUbLg"
        api_base = "https://api.minimaxi.com/anthropic"

        os.environ['ANTHROPIC_BASE_URL'] = api_base
        os.environ['ANTHROPIC_AUTH_TOKEN'] = api_key

        print(f"Testing Anthropic client with base URL: {api_base}")

        client = anthropic.Anthropic()

        message = client.messages.create(
            model="MiniMax-M2.7",
            max_tokens=100,
            messages=[
                {"role": "user", "content": [{"type": "text", "text": "Hello, respond with 'OK'"}]}
            ]
        )

        print(f"Message content blocks: {message.content}")

        content = ""
        for block in message.content:
            print(f"Block type: {block.type}")
            if block.type == "text":
                content += block.text

        print(f"[SUCCESS] Response: {content}")
        return True

    except Exception as e:
        print(f"[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_anthropic())
