"""
Global configuration settings for AI Data Agent.
"""
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "AI Data Agent"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "your-secret-key-change-in-production"

    # Database
    DATABASE_URL: str = "mysql+aiomysql://user:password@localhost:3306/data_agent"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # LLM Configuration
    LLM_PROVIDER: str = "openai"
    LLM_API_KEY: str = ""
    LLM_API_BASE: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4096

    # Authentication
    JWT_SECRET_KEY: str = "your-jwt-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # API Auth Encryption (for encrypting auth_config in database)
    API_AUTH_ENCRYPTION_KEY: str = ""  # Set via environment variable

    # Embedding Configuration (for API retrieval)
    EMBEDDING_PROVIDER: str = "local"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSIONS: int = 384

    # Vector Store Configuration (Qdrant)
    # Use file:// for persistent storage, or :memory: for in-memory mode
    QDRANT_URL: str = "file://./data/qdrant"
    QDRANT_COLLECTION: str = "api_embeddings"

    # API Retrieval Configuration
    API_RETRIEVAL_CANDIDATE_TOP_K: int = 100  # Stage 1: Vector similarity search
    API_RETRIEVAL_FINAL_TOP_K: int = 10  # Stage 2: LLM refinement
    API_RETRIEVAL_CACHE_TTL: int = 300  # Cache TTL in seconds (5 minutes)

    # Permission
    ENABLE_PERMISSION_CHECK: bool = True
    DEFAULT_DATA_SCOPE: str = "department"

    # Logging
    LOG_LEVEL: str = "DEBUG"
    LOG_FILE: str = "logs/app.log"

    # ReAct Loop Circuit Breaker
    REACT_MAX_ITERATIONS: int = 10
    REACT_MAX_TOKENS_PER_QUERY: int = 8000
    REACT_TOOL_TIMEOUT_SECONDS: int = 30
    REACT_LOOP_TIMEOUT_SECONDS: int = 120
    REACT_CIRCUIT_FAILURE_THRESHOLD: int = 3  # Consecutive failures to trigger OPEN
    REACT_CIRCUIT_RECOVERY_TIMEOUT: float = 30.0  # Seconds before attempting recovery

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()