"""Application configuration using pydantic-settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Service
    service_name: str = "prompt-service"
    service_port: int = 8080
    log_level: str = "INFO"

    # PostgreSQL
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "llmops"
    postgres_password: str = ""
    postgres_db: str = "llmops"

    # NATS
    nats_url: str = "nats://nats:4222"

    # Elasticsearch
    elasticsearch_url: str = "http://elasticsearch:9200"

    # LLM Providers
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    groq_api_key: str = ""
    default_llm_provider: str = "groq"

    @property
    def database_url(self) -> str:
        """Construct async database URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        """Construct sync database URL for migrations."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
