"""Tests for indexer components."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestMilvusIndexer:
    """Tests for MilvusIndexer."""

    @pytest.fixture
    def indexer(self):
        from app.components.indexers import MilvusIndexer
        return MilvusIndexer()

    def test_name(self, indexer):
        """Test indexer name."""
        assert indexer.name == "milvus"

    def test_category(self, indexer):
        """Test indexer category."""
        assert indexer.category == "indexers"

    @pytest.mark.asyncio
    async def test_index_vectors(self, indexer):
        """Test indexing vectors."""
        vectors = [[0.1] * 1536, [0.2] * 1536]
        ids = ["id1", "id2"]
        metadata = [{"doc": "1"}, {"doc": "2"}]

        mock_collection = MagicMock()
        mock_collection.insert = MagicMock(return_value=MagicMock(primary_keys=ids))

        with patch.object(indexer, '_get_collection', return_value=mock_collection):
            result = await indexer.index(
                vectors=vectors,
                ids=ids,
                metadata=metadata,
                collection_name="test_collection",
                dimension=1536,
            )

            assert result["indexed_count"] == 2
            assert result["ids"] == ids

    @pytest.mark.asyncio
    async def test_index_empty_vectors(self, indexer):
        """Test indexing empty vectors."""
        result = await indexer.index(
            vectors=[],
            ids=[],
            metadata=[],
            collection_name="test_collection",
            dimension=1536,
        )

        assert result["indexed_count"] == 0

    @pytest.mark.asyncio
    async def test_delete_vectors(self, indexer):
        """Test deleting vectors."""
        ids = ["id1", "id2"]

        mock_collection = MagicMock()
        mock_collection.delete = MagicMock()

        with patch.object(indexer, '_get_collection', return_value=mock_collection):
            result = await indexer.delete(
                ids=ids,
                collection_name="test_collection",
            )

            assert result["deleted_count"] == 2

    @pytest.mark.asyncio
    async def test_create_collection(self, indexer):
        """Test collection creation."""
        mock_utility = MagicMock()
        mock_utility.has_collection.return_value = False

        with patch('app.components.indexers.milvus.utility', mock_utility):
            with patch('app.components.indexers.milvus.Collection') as mock_coll:
                await indexer.create_collection(
                    collection_name="new_collection",
                    dimension=1536,
                )

                mock_coll.assert_called_once()

    def test_config_schema(self, indexer):
        """Test config schema."""
        schema = indexer.get_config_schema()

        assert "properties" in schema
        assert "collection_name" in schema["properties"]
        assert "dimension" in schema["properties"]


class TestElasticsearchIndexer:
    """Tests for ElasticsearchIndexer."""

    @pytest.fixture
    def indexer(self):
        from app.components.indexers import ElasticsearchIndexer
        return ElasticsearchIndexer()

    def test_name(self, indexer):
        """Test indexer name."""
        assert indexer.name == "elasticsearch"

    def test_category(self, indexer):
        """Test indexer category."""
        assert indexer.category == "indexers"

    @pytest.mark.asyncio
    async def test_index_documents(self, indexer):
        """Test indexing documents."""
        documents = [
            {"id": "1", "content": "doc 1", "metadata": {}},
            {"id": "2", "content": "doc 2", "metadata": {}},
        ]

        mock_client = MagicMock()
        mock_client.bulk = AsyncMock(return_value={"items": documents, "errors": False})

        with patch.object(indexer, '_get_client', return_value=mock_client):
            result = await indexer.index(
                documents=documents,
                index_name="test_index",
            )

            assert result["indexed_count"] == 2

    @pytest.mark.asyncio
    async def test_index_empty_documents(self, indexer):
        """Test indexing empty documents."""
        result = await indexer.index(
            documents=[],
            index_name="test_index",
        )

        assert result["indexed_count"] == 0

    @pytest.mark.asyncio
    async def test_delete_documents(self, indexer):
        """Test deleting documents."""
        ids = ["id1", "id2"]

        mock_client = MagicMock()
        mock_client.delete_by_query = AsyncMock(return_value={"deleted": 2})

        with patch.object(indexer, '_get_client', return_value=mock_client):
            result = await indexer.delete(
                ids=ids,
                index_name="test_index",
            )

            assert result["deleted_count"] == 2

    @pytest.mark.asyncio
    async def test_create_index(self, indexer):
        """Test index creation."""
        mock_client = MagicMock()
        mock_client.indices.exists = AsyncMock(return_value=False)
        mock_client.indices.create = AsyncMock()

        with patch.object(indexer, '_get_client', return_value=mock_client):
            await indexer.create_index(
                index_name="new_index",
            )

            mock_client.indices.create.assert_called_once()

    def test_config_schema(self, indexer):
        """Test config schema."""
        schema = indexer.get_config_schema()

        assert "properties" in schema
        assert "index_name" in schema["properties"]


class TestIndexerFactory:
    """Tests for IndexerFactory."""

    def test_create_milvus_indexer(self):
        """Test creating Milvus indexer."""
        from app.components.indexers import IndexerFactory

        indexer = IndexerFactory.create("milvus")
        assert indexer is not None
        assert indexer.name == "milvus"

    def test_create_elasticsearch_indexer(self):
        """Test creating Elasticsearch indexer."""
        from app.components.indexers import IndexerFactory

        indexer = IndexerFactory.create("elasticsearch")
        assert indexer is not None
        assert indexer.name == "elasticsearch"

    def test_list_available(self):
        """Test listing available indexers."""
        from app.components.indexers import IndexerFactory

        indexers = IndexerFactory.list_available()
        assert len(indexers) >= 2
        names = [i["name"] for i in indexers]
        assert "milvus" in names
        assert "elasticsearch" in names

    def test_create_invalid_indexer(self):
        """Test creating invalid indexer raises error."""
        from app.components.indexers import IndexerFactory
        from app.components.base import ComponentNotFoundError

        with pytest.raises(ComponentNotFoundError):
            IndexerFactory.create("nonexistent")
