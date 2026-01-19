"""
Configuration management for Guardrails Service.
Loads settings from environment variables with fallback to .env file.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Service Configuration
    service_name: str = "guardrails-service"
    service_port: int = 8083
    log_level: str = "INFO"
    environment: str = "development"

    # PostgreSQL Database Configuration
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "llmops"
    postgres_password: str = ""
    postgres_db: str = "llmops"

    # Database Connection Pool Settings
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_pre_ping: bool = True
    db_echo: bool = False

    # LLM Provider Configuration
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    groq_api_key: str = ""
    default_llm_provider: str = "groq"

    # LLM Model Configuration
    default_model: str = "llama-3.3-70b-versatile"
    default_temperature: float = 0.7
    default_max_tokens: int = 2000

    # API Configuration
    api_v1_prefix: str = "/api/v1"
    cors_origins: list = ["*"]

    # Message Queue Configuration (NATS)
    nats_url: str = "nats://nats:4222"
    nats_max_reconnect_attempts: int = 60
    nats_reconnect_time_wait: int = 2

    # Elasticsearch Configuration
    elasticsearch_url: str = "http://elasticsearch:9200"
    elasticsearch_index_prefix: str = "guardrails"

    # Pagination
    default_page_size: int = 20
    max_page_size: int = 100

    @property
    def database_url(self) -> str:
        """Construct async PostgreSQL database URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        """Construct sync PostgreSQL database URL (for migrations)."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to ensure single instance across application.
    """
    return Settings()
