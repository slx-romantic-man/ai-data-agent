"""
LLM client configuration for AI Data Agent.
Supports OpenAI, Aliyun, and Anthropic (MiniMax) LLM APIs.
"""
from typing import Optional, Dict, Any, List, AsyncGenerator
from abc import ABC, abstractmethod
import threading
import httpx
import json
import asyncio
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger()


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Send chat completion request."""
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """Send chat completion request with streaming."""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI API client."""

    def __init__(
        self,
        api_key: str,
        api_base: str = "https://api.openai.com/v1",
        model: str = "gpt-4",
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ):
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = httpx.AsyncClient(timeout=120.0)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Send chat completion request with retry mechanism."""
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }

        logger.info(f"LLM Request: {url}")
        logger.debug(f"LLM Payload: {json.dumps(payload, ensure_ascii=False)[:500]}")

        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                response = await self.client.post(url, headers=headers, json=payload)
                logger.info(f"LLM Response Status: {response.status_code}")

                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"LLM Error Response: {error_text}")
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    raise Exception(f"LLM API error {response.status_code}: {error_text}")

                data = response.json()
                logger.info(f"LLM Response Data: {json.dumps(data, ensure_ascii=False)[:1000]}")
                content = data["choices"][0]["message"]["content"]
                logger.info(f"LLM Content Length: {len(content)}")
                return content

            except httpx.RequestError as e:
                logger.error(f"LLM Request Error: {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                raise Exception(f"LLM connection failed after {max_retries} retries: {str(e)}")

        raise Exception("LLM request failed after all retries")

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """Send chat completion request with streaming."""
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "stream": True,
        }

        async with self.client.stream("POST", url, headers=headers, json=payload) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        if chunk["choices"][0]["delta"].get("content"):
                            yield chunk["choices"][0]["delta"]["content"]
                    except json.JSONDecodeError:
                        continue


class AliyunLLMClient(BaseLLMClient):
    """Aliyun DashScope LLM API client."""

    def __init__(
        self,
        api_key: str,
        api_base: str = "https://dashscope.aliyuncs.com/api/v1",
        model: str = "qwen-max",
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ):
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = httpx.AsyncClient(timeout=120.0)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Send chat completion request to Aliyun."""
        url = f"{self.api_base}/services/aigc/text-generation/generation"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": {
                "messages": messages
            },
            "parameters": {
                "temperature": temperature or self.temperature,
                "max_tokens": max_tokens or self.max_tokens,
            }
        }

        logger.info(f"Aliyun LLM Request: {url}")
        logger.debug(f"Aliyun LLM Payload: {json.dumps(payload, ensure_ascii=False)[:500]}")

        try:
            response = await self.client.post(url, headers=headers, json=payload)
            logger.info(f"Aliyun LLM Response Status: {response.status_code}")

            if response.status_code != 200:
                error_text = response.text
                logger.error(f"Aliyun LLM Error Response: {error_text}")
                raise Exception(f"Aliyun LLM API error {response.status_code}: {error_text}")

            data = response.json()
            return data["output"]["text"]
        except httpx.RequestError as e:
            logger.error(f"Aliyun LLM Request Error: {str(e)}")
            raise Exception(f"Aliyun LLM connection failed: {str(e)}")

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """Send chat completion request with streaming to Aliyun."""
        url = f"{self.api_base}/services/aigc/text-generation/generation"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-SSE": "enable",
        }
        payload = {
            "model": self.model,
            "input": {
                "messages": messages
            },
            "parameters": {
                "temperature": temperature or self.temperature,
                "max_tokens": max_tokens or self.max_tokens,
                "incremental_output": True,
            }
        }

        async with self.client.stream("POST", url, headers=headers, json=payload) as response:
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    data = line[5:].strip()
                    try:
                        chunk = json.loads(data)
                        if chunk.get("output", {}).get("text"):
                            yield chunk["output"]["text"]
                    except json.JSONDecodeError:
                        continue


class AnthropicClient(BaseLLMClient):
    """Anthropic-compatible API client (for MiniMax)."""

    def __init__(
        self,
        api_key: str,
        api_base: str = "https://api.minimaxi.com/anthropic",
        model: str = "MiniMax-M2.7",
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ):
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Send chat completion request using Anthropic SDK."""
        try:
            import anthropic
            import os

            os.environ['ANTHROPIC_BASE_URL'] = self.api_base
            os.environ['ANTHROPIC_AUTH_TOKEN'] = self.api_key

            client = anthropic.Anthropic()

            # Convert messages format
            system_msg = ""
            user_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_msg = msg["content"]
                else:
                    user_messages.append({
                        "role": msg["role"],
                        "content": [{"type": "text", "text": msg["content"]}]
                    })

            logger.info(f"Anthropic Request: {self.api_base}")

            message = client.messages.create(
                model=self.model,
                max_tokens=max_tokens or self.max_tokens,
                system=system_msg,
                messages=user_messages,
                temperature=temperature or self.temperature,
            )

            logger.info(f"Anthropic Response received")

            if message is None:
                logger.error("Anthropic response is None")
                return ""

            # Extract text content
            content = ""
            if message.content:
                for block in message.content:
                    if block.type == "text":
                        content += block.text
            else:
                logger.warning("Anthropic response has no content")

            logger.info(f"Anthropic Content Length: {len(content)}")
            return content

        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            raise

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """Send chat completion request with streaming."""
        try:
            import anthropic
            import os

            os.environ['ANTHROPIC_BASE_URL'] = self.api_base
            os.environ['ANTHROPIC_AUTH_TOKEN'] = self.api_key

            client = anthropic.Anthropic()

            # Convert messages format
            system_msg = ""
            user_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_msg = msg["content"]
                else:
                    user_messages.append({
                        "role": msg["role"],
                        "content": [{"type": "text", "text": msg["content"]}]
                    })

            with client.messages.stream(
                model=self.model,
                max_tokens=max_tokens or self.max_tokens,
                system=system_msg,
                messages=user_messages,
                temperature=temperature or self.temperature,
            ) as stream:
                for text in stream.text_stream:
                    yield text

        except Exception as e:
            logger.error(f"Anthropic streaming error: {str(e)}")
            raise


def get_llm_client() -> BaseLLMClient:
    """Factory function to create LLM client based on configuration."""
    provider = settings.LLM_PROVIDER.lower()

    if provider == "openai":
        return OpenAIClient(
            api_key=settings.LLM_API_KEY,
            api_base=settings.LLM_API_BASE,
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
    elif provider == "aliyun":
        return AliyunLLMClient(
            api_key=settings.LLM_API_KEY,
            api_base=settings.LLM_API_BASE,
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
    elif provider == "anthropic":
        return AnthropicClient(
            api_key=settings.LLM_API_KEY,
            api_base=settings.LLM_API_BASE,
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


# Global LLM client instance
_llm_client: Optional[BaseLLMClient] = None
_client_lock = threading.Lock()


def get_llm() -> BaseLLMClient:
    """
    Get or create LLM client instance (thread-safe).

    Uses double-checked locking to ensure thread safety
    while avoiding the lock overhead after initialization.
    """
    global _llm_client
    if _llm_client is None:
        with _client_lock:
            if _llm_client is None:  # Double-check
                _llm_client = get_llm_client()
    return _llm_client