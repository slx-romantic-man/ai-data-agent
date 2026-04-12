"""
LLM Response Cache - In-memory LRU cache for LLM responses.

Reduces redundant LLM calls by caching responses based on the input messages.
Used by intent, planner, and analyzer nodes.
"""
import hashlib
import json
import unicodedata
from typing import Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


class LLMResponseCache:
    """In-memory LRU cache for LLM responses."""

    def __init__(self, max_size: int = 512):
        self._cache: dict = {}
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _normalize_messages(messages: list) -> list:
        """Normalize messages for deterministic key generation.

        Strips whitespace from string content and applies Unicode NFKC
        normalization before serialization.
        """
        normalized = []
        for msg in messages:
            if isinstance(msg, dict):
                norm_msg = {}
                for k, v in msg.items():
                    if isinstance(v, str):
                        norm_msg[k] = unicodedata.normalize("NFKC", v.strip())
                    else:
                        norm_msg[k] = v
                normalized.append(norm_msg)
            else:
                normalized.append(msg)
        return normalized

    def _make_key(self, messages: list) -> str:
        """Create deterministic cache key from messages."""
        normalized = self._normalize_messages(messages)
        content = json.dumps(normalized, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def get(self, messages: list) -> Optional[str]:
        """Get cached response for the given messages."""
        key = self._make_key(messages)
        if key in self._cache:
            self._hits += 1
            # Move to end (most recently used)
            value = self._cache.pop(key)
            self._cache[key] = value
            logger.debug(f"[LLMCache] Hit - key={key[:16]}... hits={self._hits} misses={self._misses}")
            return value
        self._misses += 1
        logger.debug(f"[LLMCache] Miss - key={key[:16]}... hits={self._hits} misses={self._misses}")
        return None

    def set(self, messages: list, response: str):
        """Cache a response for the given messages."""
        key = self._make_key(messages)
        if key in self._cache:
            self._cache.pop(key)
        elif len(self._cache) >= self._max_size:
            # Remove oldest (first) entry
            self._cache.pop(next(iter(self._cache)))
            logger.debug(f"[LLMCache] Evicted oldest entry - cache full at {self._max_size}")
        self._cache[key] = response
        logger.debug(f"[LLMCache] Set - key={key[:16]}... size={len(self._cache)}/{self._max_size}")

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total


# Global cache instance
_llm_cache = LLMResponseCache(max_size=512)


def get_llm_cache() -> LLMResponseCache:
    """Get the global LLM response cache instance."""
    return _llm_cache
