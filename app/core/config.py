"""Application configuration management."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "SmartShop AI"
    APP_VERSION: str = "1.0.0"
    ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8080  # Changed from 8000 to avoid port conflicts

    # OpenAI
    OPENAI_API_KEY: str = "sk-placeholder-key-not-set"  # Default placeholder
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_MAX_TOKENS: int = 1500
    OPENAI_TEMPERATURE: float = 0.7

    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/smartshop_ai"  # Default
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 3600
    CACHE_MAX_SIZE: int = 1000

    # Session
    SESSION_SECRET_KEY: str = "your-secret-key-change-in-production"
    SESSION_EXPIRE_MINUTES: int = 30

    # Vector Store
    VECTOR_STORE_PATH: str = "./data/embeddings/faiss_index"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536

    # Agent Configuration
    AGENT_TIMEOUT_SECONDS: int = 30
    AGENT_MAX_RETRIES: int = 3
    AGENT_RETRY_DELAY_SECONDS: int = 1

    # Rate Limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 10

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8501"]
    CORS_ALLOW_CREDENTIALS: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
