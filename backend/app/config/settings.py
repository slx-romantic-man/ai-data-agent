"""
Global configuration settings for AI Data Agent.
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file="/app/.env",  # Container path; use "../../../.env" for local dev
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    # Application
    APP_NAME: str = "AI Data Agent"
    APP_ENV: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = ""

    # Database
    DATABASE_URL: str = ""  # Must be set via environment variable
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # PostgreSQL for LangGraph Checkpointer
    POSTGRES_URL: str = ""  # Must be set via environment variable

    # LLM Configuration
    LLM_PROVIDER: str = "openai"
    LLM_API_KEY: str = ""
    LLM_API_BASE: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4096

    # Authentication
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # CIA Login Configuration
    CIA_ENABLED: bool = False
    CIA_URL: str = "https://sso.example.com"
    CIA_ACCESS_CLIENT_ID: str = ""
    CIA_CLIENT_SECRET: str = ""
    CIA_APP_KEY: str = ""      # findUserWithToken 所需
    CIA_APP_SECRET: str = ""   # findUserWithToken 所需
    AUTH_MODE: str = "local_only"  # dual, cia_only, local_only

    # API Auth Encryption (for encrypting auth_config in database)
    API_AUTH_ENCRYPTION_KEY: str = ""  # Set via environment variable

    # Embedding Configuration (for API retrieval)
    # Provider: "local" (sentence-transformers) or "openai" (OpenAI-compatible API)
    EMBEDDING_PROVIDER: str = "openai"
    EMBEDDING_MODEL: str = "text-embedding-v3"
    EMBEDDING_API_KEY: str = ""  # API key for remote embedding service
    EMBEDDING_API_BASE: str = "https://api.openai.com/v1"  # Base URL for remote embedding service
    EMBEDDING_DIMENSIONS: int = 1024

    # Vector Store Configuration (Qdrant)
    # Use file:// for persistent storage, or :memory: for in-memory mode
    QDRANT_URL: str = ":memory:"
    QDRANT_COLLECTION: str = "api_embeddings"

    # API Retrieval Configuration
    API_RETRIEVAL_CANDIDATE_TOP_K: int = 100  # Stage 1: Vector similarity search
    API_RETRIEVAL_FINAL_TOP_K: int = 10  # Stage 2: LLM refinement
    API_RETRIEVAL_CACHE_TTL: int = 300  # Cache TTL in seconds (5 minutes)

    # Permission
    ENABLE_PERMISSION_CHECK: bool = True
    DEFAULT_DATA_SCOPE: str = "department"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    # ReAct Loop Circuit Breaker
    REACT_MAX_ITERATIONS: int = 10
    REACT_MAX_TOKENS_PER_QUERY: int = 8000
    REACT_TOOL_TIMEOUT_SECONDS: int = 30
    REACT_LOOP_TIMEOUT_SECONDS: int = 120
    REACT_CIRCUIT_FAILURE_THRESHOLD: int = 3  # Consecutive failures to trigger OPEN
    REACT_CIRCUIT_RECOVERY_TIMEOUT: float = 30.0  # Seconds before attempting recovery


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()