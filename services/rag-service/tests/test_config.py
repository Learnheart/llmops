"""Tests for configuration management."""

import pytest
from unittest.mock import patch
import os


class TestSettings:
    """Tests for Settings class."""

    def test_default_values(self):
        """Test default configuration values."""
        with patch.dict(os.environ, {}, clear=True):
            # Force reload of settings
            from app.config import Settings

            settings = Settings()

            # Service defaults
            assert settings.service_name == "rag-service"
            assert settings.service_port == 8084
            assert settings.log_level == "INFO"
            assert settings.environment == "development"

            # Database defaults
            assert settings.postgres_host == "postgres"
            assert settings.postgres_port == 5432
            assert settings.postgres_user == "llmops"
            assert settings.postgres_db == "llmops"

            # Pool defaults
            assert settings.db_pool_size == 10
            assert settings.db_max_overflow == 20
            assert settings.db_pool_pre_ping is True
            assert settings.db_echo is False

            # MinIO defaults
            assert settings.minio_endpoint == "minio:9000"
            assert settings.minio_access_key == "minioadmin"
            assert settings.minio_secure is False
            assert settings.minio_bucket_documents == "knowledge-docs"

            # Milvus defaults
            assert settings.milvus_host == "milvus"
            assert settings.milvus_port == 19530
            assert settings.milvus_collection_prefix == "rag_"

            # Elasticsearch defaults
            assert settings.elasticsearch_url == "http://elasticsearch:9200"
            assert settings.elasticsearch_index_prefix == "rag_"

            # Redis defaults
            assert settings.redis_url == "redis://redis:6379/0"

            # OpenAI defaults
            assert settings.openai_embedding_model == "text-embedding-3-small"

            # Local embedding defaults
            assert settings.local_embedding_model == "all-MiniLM-L6-v2"

            # NATS defaults
            assert settings.nats_url == "nats://nats:4222"
            assert settings.nats_max_reconnect_attempts == 60
            assert settings.nats_reconnect_time_wait == 2

            # API defaults
            assert settings.api_v1_prefix == "/api/v1"
            assert settings.cors_origins == ["*"]

            # Pagination defaults
            assert settings.default_page_size == 20
            assert settings.max_page_size == 100

            # Pipeline defaults
            assert settings.default_chunk_size == 512
            assert settings.default_chunk_overlap == 50
            assert settings.default_top_k == 5

    def test_environment_variable_override(self):
        """Test that environment variables override defaults."""
        env_vars = {
            "SERVICE_NAME": "custom-rag-service",
            "SERVICE_PORT": "9000",
            "LOG_LEVEL": "DEBUG",
            "POSTGRES_HOST": "custom-postgres",
            "POSTGRES_PORT": "5433",
            "MINIO_ENDPOINT": "custom-minio:9001",
            "OPENAI_API_KEY": "sk-test-key",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            from app.config import Settings

            settings = Settings()

            assert settings.service_name == "custom-rag-service"
            assert settings.service_port == 9000
            assert settings.log_level == "DEBUG"
            assert settings.postgres_host == "custom-postgres"
            assert settings.postgres_port == 5433
            assert settings.minio_endpoint == "custom-minio:9001"
            assert settings.openai_api_key == "sk-test-key"

    def test_database_url_property(self):
        """Test database_url property construction."""
        with patch.dict(os.environ, {
            "POSTGRES_USER": "testuser",
            "POSTGRES_PASSWORD": "testpass",
            "POSTGRES_HOST": "testhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "testdb",
        }, clear=False):
            from app.config import Settings

            settings = Settings()

            expected = "postgresql+asyncpg://testuser:testpass@testhost:5432/testdb"
            assert settings.database_url == expected

    def test_sync_database_url_property(self):
        """Test sync_database_url property construction."""
        with patch.dict(os.environ, {
            "POSTGRES_USER": "testuser",
            "POSTGRES_PASSWORD": "testpass",
            "POSTGRES_HOST": "testhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "testdb",
        }, clear=False):
            from app.config import Settings

            settings = Settings()

            expected = "postgresql://testuser:testpass@testhost:5432/testdb"
            assert settings.sync_database_url == expected

    def test_database_url_with_special_characters_in_password(self):
        """Test database URL with special characters in password."""
        with patch.dict(os.environ, {
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": "p@ss:word/123",
            "POSTGRES_HOST": "host",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "db",
        }, clear=False):
            from app.config import Settings

            settings = Settings()

            # Password with special chars should be included as-is
            assert "p@ss:word/123" in settings.database_url

    def test_cors_origins_list(self):
        """Test CORS origins as list."""
        from app.config import Settings

        settings = Settings()

        # Default should be a list
        assert isinstance(settings.cors_origins, list)
        assert "*" in settings.cors_origins

    def test_boolean_settings(self):
        """Test boolean settings."""
        with patch.dict(os.environ, {
            "MINIO_SECURE": "true",
            "DB_POOL_PRE_PING": "false",
            "DB_ECHO": "true",
        }, clear=False):
            from app.config import Settings

            settings = Settings()

            assert settings.minio_secure is True
            assert settings.db_pool_pre_ping is False
            assert settings.db_echo is True

    def test_integer_settings(self):
        """Test integer settings parsing."""
        with patch.dict(os.environ, {
            "SERVICE_PORT": "9999",
            "DB_POOL_SIZE": "50",
            "DEFAULT_CHUNK_SIZE": "1024",
            "DEFAULT_TOP_K": "10",
        }, clear=False):
            from app.config import Settings

            settings = Settings()

            assert settings.service_port == 9999
            assert settings.db_pool_size == 50
            assert settings.default_chunk_size == 1024
            assert settings.default_top_k == 10


class TestGetSettings:
    """Tests for get_settings function."""

    def test_get_settings_returns_settings(self):
        """Test that get_settings returns a Settings instance."""
        from app.config import get_settings

        settings = get_settings()

        assert settings is not None
        assert hasattr(settings, "service_name")
        assert hasattr(settings, "database_url")

    def test_get_settings_caching(self):
        """Test that get_settings uses caching."""
        # Clear the cache first
        from app.config import get_settings
        get_settings.cache_clear()

        settings1 = get_settings()
        settings2 = get_settings()

        # Should return the same instance due to caching
        assert settings1 is settings2

    def test_get_settings_after_cache_clear(self):
        """Test get_settings after cache clear."""
        from app.config import get_settings

        settings1 = get_settings()

        # Clear cache
        get_settings.cache_clear()

        settings2 = get_settings()

        # After cache clear, should create new instance
        # (but values should be the same)
        assert settings1.service_name == settings2.service_name


class TestSettingsValidation:
    """Tests for settings validation."""

    def test_empty_password_allowed(self):
        """Test that empty password is allowed (for dev)."""
        with patch.dict(os.environ, {
            "POSTGRES_PASSWORD": "",
        }, clear=False):
            from app.config import Settings

            settings = Settings()

            assert settings.postgres_password == ""

    def test_empty_api_key_allowed(self):
        """Test that empty API key is allowed."""
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "",
        }, clear=False):
            from app.config import Settings

            settings = Settings()

            assert settings.openai_api_key == ""

    def test_production_environment_setting(self):
        """Test production environment setting."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
        }, clear=False):
            from app.config import Settings

            settings = Settings()

            assert settings.environment == "production"

    def test_case_insensitive_env_vars(self):
        """Test that environment variables are case insensitive."""
        # pydantic-settings handles case insensitivity
        with patch.dict(os.environ, {
            "service_name": "lowercase-service",
        }, clear=False):
            from app.config import Settings

            settings = Settings()

            # Should pick up lowercase env var
            assert settings.service_name == "lowercase-service"


class TestSettingsIntegration:
    """Integration tests for settings."""

    def test_all_required_settings_present(self):
        """Test that all required settings are present."""
        from app.config import Settings

        settings = Settings()

        # Database settings
        assert hasattr(settings, "postgres_host")
        assert hasattr(settings, "postgres_port")
        assert hasattr(settings, "postgres_user")
        assert hasattr(settings, "postgres_password")
        assert hasattr(settings, "postgres_db")

        # Service settings
        assert hasattr(settings, "service_name")
        assert hasattr(settings, "service_port")

        # External services
        assert hasattr(settings, "minio_endpoint")
        assert hasattr(settings, "milvus_host")
        assert hasattr(settings, "elasticsearch_url")
        assert hasattr(settings, "redis_url")
        assert hasattr(settings, "nats_url")

        # ML/AI settings
        assert hasattr(settings, "openai_api_key")
        assert hasattr(settings, "openai_embedding_model")
        assert hasattr(settings, "local_embedding_model")

    def test_database_urls_are_valid_format(self):
        """Test that database URLs have valid format."""
        from app.config import Settings

        settings = Settings()

        # Async URL should start with postgresql+asyncpg://
        assert settings.database_url.startswith("postgresql+asyncpg://")

        # Sync URL should start with postgresql://
        assert settings.sync_database_url.startswith("postgresql://")

    def test_settings_can_be_serialized(self):
        """Test that settings can be converted to dict."""
        from app.config import Settings

        settings = Settings()

        # Should be able to convert to dict
        settings_dict = settings.model_dump()

        assert isinstance(settings_dict, dict)
        assert "service_name" in settings_dict
        assert "postgres_host" in settings_dict
