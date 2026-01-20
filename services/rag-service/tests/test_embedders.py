"""Tests for embedder components."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import numpy as np


class TestOpenAIEmbedder:
    """Tests for OpenAIEmbedder."""

    @pytest.fixture
    def embedder(self):
        from app.components.embedders import OpenAIEmbedder
        return OpenAIEmbedder()

    def test_name(self, embedder):
        """Test embedder name."""
        assert embedder.name == "openai"

    def test_default_model(self, embedder):
        """Test default model."""
        assert embedder.default_model == "text-embedding-3-small"

    def test_supported_models(self, embedder):
        """Test supported models list."""
        models = embedder.supported_models
        assert "text-embedding-3-small" in models
        assert "text-embedding-3-large" in models
        assert "text-embedding-ada-002" in models

    def test_get_dimension(self, embedder):
        """Test dimension retrieval for models."""
        assert embedder.get_dimension("text-embedding-3-small") == 1536
        assert embedder.get_dimension("text-embedding-3-large") == 3072
        assert embedder.get_dimension("text-embedding-ada-002") == 1536

    @pytest.mark.asyncio
    async def test_embed_single_text(self, embedder):
        """Test embedding single text."""
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]

        with patch.object(embedder, '_get_client') as mock_client:
            mock_client.return_value.embeddings.create = AsyncMock(return_value=mock_response)

            result = await embedder.embed(["test text"])

            assert len(result) == 1
            assert len(result[0]) == 1536

    @pytest.mark.asyncio
    async def test_embed_batch(self, embedder):
        """Test embedding batch of texts."""
        texts = ["text 1", "text 2", "text 3"]
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536) for _ in texts]

        with patch.object(embedder, '_get_client') as mock_client:
            mock_client.return_value.embeddings.create = AsyncMock(return_value=mock_response)

            result = await embedder.embed(texts)

            assert len(result) == 3

    @pytest.mark.asyncio
    async def test_embed_empty_list(self, embedder):
        """Test embedding empty list."""
        result = await embedder.embed([])
        assert result == []

    def test_config_schema(self, embedder):
        """Test config schema."""
        schema = embedder.get_config_schema()

        assert "properties" in schema
        assert "model" in schema["properties"]
        assert "batch_size" in schema["properties"]


class TestLocalEmbedder:
    """Tests for LocalEmbedder."""

    @pytest.fixture
    def embedder(self):
        from app.components.embedders import LocalEmbedder
        return LocalEmbedder()

    def test_name(self, embedder):
        """Test embedder name."""
        assert embedder.name == "local"

    def test_default_model(self, embedder):
        """Test default model."""
        assert "all-MiniLM" in embedder.default_model or embedder.default_model is not None

    @pytest.mark.asyncio
    async def test_embed_with_mock_model(self, embedder):
        """Test embedding with mocked model."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1] * 384, [0.2] * 384])

        with patch.object(embedder, '_get_model', return_value=mock_model):
            result = await embedder.embed(["text 1", "text 2"])

            assert len(result) == 2
            assert len(result[0]) == 384

    @pytest.mark.asyncio
    async def test_embed_empty_list(self, embedder):
        """Test embedding empty list."""
        result = await embedder.embed([])
        assert result == []

    def test_config_schema(self, embedder):
        """Test config schema."""
        schema = embedder.get_config_schema()

        assert "properties" in schema
        assert "model" in schema["properties"]


class TestEmbedderFactory:
    """Tests for EmbedderFactory."""

    def test_create_openai_embedder(self):
        """Test creating OpenAI embedder."""
        from app.components.embedders import EmbedderFactory

        embedder = EmbedderFactory.create("openai")
        assert embedder is not None
        assert embedder.name == "openai"

    def test_create_local_embedder(self):
        """Test creating local embedder."""
        from app.components.embedders import EmbedderFactory

        embedder = EmbedderFactory.create("local")
        assert embedder is not None
        assert embedder.name == "local"

    def test_list_available(self):
        """Test listing available embedders."""
        from app.components.embedders import EmbedderFactory

        embedders = EmbedderFactory.list_available()
        assert len(embedders) >= 2
        names = [e["name"] for e in embedders]
        assert "openai" in names
        assert "local" in names

    def test_create_invalid_embedder(self):
        """Test creating invalid embedder raises error."""
        from app.components.embedders import EmbedderFactory
        from app.components.base import ComponentNotFoundError

        with pytest.raises(ComponentNotFoundError):
            EmbedderFactory.create("nonexistent")
