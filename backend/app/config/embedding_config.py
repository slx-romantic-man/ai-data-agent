"""
Embedding client configuration for AI Data Agent.
Supports local (sentence-transformers) and remote (OpenAI-compatible) embedding APIs.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
import httpx
import json
import time
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger()


class BaseEmbeddingClient(ABC):
    """Abstract base class for embedding clients."""

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        pass


class LocalEmbeddingClient(BaseEmbeddingClient):
    """Local embedding client using sentence-transformers."""

    def __init__(self, model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model
        self._model = None

    def _load_model(self):
        """Lazy load the sentence-transformers model."""
        if self._model is None:
            import os
            os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded successfully")

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using local model."""
        self._load_model()
        embeddings = self._model.encode(texts)
        # Handle both single text and batch
        if len(texts) == 1:
            return [embeddings.tolist()]
        return embeddings.tolist()


class OpenAIEmbeddingClient(BaseEmbeddingClient):
    """
    OpenAI-compatible embedding API client.
    Works with OpenAI, Aliyun DashScope, Zhipu, Kimi, and any OpenAI-compatible provider.
    """

    def __init__(
        self,
        api_key: str,
        api_base: str = "https://api.openai.com/v1",
        model: str = "text-embedding-3-small",
    ):
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")
        self.model = model
        self.client = httpx.Client(timeout=60.0)

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI-compatible API."""
        # OpenAI-compatible endpoint: /v1/embeddings
        # Handle base URLs that may or may not include /v1
        if self.api_base.endswith("/v1"):
            url = f"{self.api_base}/embeddings"
        else:
            url = f"{self.api_base}/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": texts,
        }

        logger.info(f"Embedding Request: {url} | texts: {len(texts)} | model: {self.model}")

        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                response = self.client.post(url, headers=headers, json=payload)
                logger.info(f"Embedding Response Status: {response.status_code}")

                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"Embedding Error Response: {error_text}")
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    raise Exception(f"Embedding API error {response.status_code}: {error_text}")

                data = response.json()
                embeddings = [item["embedding"] for item in data["data"]]
                # Sort by index to ensure correct order
                indexed = [(item["index"], item["embedding"]) for item in data["data"]]
                indexed.sort(key=lambda x: x[0])
                embeddings = [emb for _, emb in indexed]

                logger.info(f"Embedding generated: {len(embeddings)} vectors, dim={len(embeddings[0]) if embeddings else 0}")
                return embeddings

            except Exception as e:
                logger.error(f"Embedding API error (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise Exception(f"Embedding API failed after {max_retries} retries: {str(e)}")


def get_embedding_client() -> BaseEmbeddingClient:
    """Factory function to create embedding client based on configuration."""
    provider = settings.EMBEDDING_PROVIDER.lower()

    if provider == "local":
        return LocalEmbeddingClient(
            model=settings.EMBEDDING_MODEL,
        )
    elif provider in ("openai", "anthropic"):
        # Both OpenAI and Anthropic-compatible providers use the same embedding API
        # Anthropic itself doesn't have embedding API, but most providers support
        # OpenAI-compatible /v1/embeddings endpoint
        return OpenAIEmbeddingClient(
            api_key=settings.EMBEDDING_API_KEY,
            api_base=settings.EMBEDDING_API_BASE,
            model=settings.EMBEDDING_MODEL,
        )
    else:
        raise ValueError(f"Unsupported embedding provider: {provider}")
