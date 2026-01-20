"""Configuration management for RAG Service."""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Service Configuration
    service_name: str = "rag-service"
    service_port: int = 8084
    log_level: str = "INFO"
    environment: str = "development"

    # PostgreSQL Configuration
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "llmops"
    postgres_password: str = ""
    postgres_db: str = "llmops"

    # Database Pool Settings
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_pre_ping: bool = True
    db_echo: bool = False

    # MinIO Configuration
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = ""
    minio_secure: bool = False
    minio_bucket_documents: str = "knowledge-docs"

    # Milvus Configuration
    milvus_host: str = "milvus"
    milvus_port: int = 19530
    milvus_collection_prefix: str = "rag_"

    # Elasticsearch Configuration
    elasticsearch_url: str = "http://elasticsearch:9200"
    elasticsearch_index_prefix: str = "rag_"

    # Redis Configuration
    redis_url: str = "redis://redis:6379/0"

    # OpenAI Configuration
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"

    # Local Embedding Model
    local_embedding_model: str = "all-MiniLM-L6-v2"

    # NATS Configuration
    nats_url: str = "nats://nats:4222"
    nats_max_reconnect_attempts: int = 60
    nats_reconnect_time_wait: int = 2

    # API Configuration
    api_v1_prefix: str = "/api/v1"
    cors_origins: List[str] = ["*"]

    # Pagination
    default_page_size: int = 20
    max_page_size: int = 100

    # Pipeline Defaults
    default_chunk_size: int = 512
    default_chunk_overlap: int = 50
    default_top_k: int = 5

    @property
    def database_url(self) -> str:
        """Construct async database URL for SQLAlchemy."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        """Construct sync database URL for Alembic migrations."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance (singleton pattern)."""
    return Settings()
