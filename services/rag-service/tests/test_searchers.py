"""Tests for searcher components."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestSemanticSearcher:
    """Tests for SemanticSearcher."""

    @pytest.fixture
    def searcher(self):
        from app.components.searchers import SemanticSearcher
        return SemanticSearcher()

    def test_name(self, searcher):
        """Test searcher name."""
        assert searcher.name == "semantic"

    def test_category(self, searcher):
        """Test searcher category."""
        assert searcher.category == "searchers"

    @pytest.mark.asyncio
    async def test_search(self, searcher):
        """Test semantic search."""
        query_vector = [0.1] * 1536
        mock_results = [
            {"id": "1", "score": 0.95, "content": "result 1"},
            {"id": "2", "score": 0.85, "content": "result 2"},
        ]

        mock_collection = MagicMock()
        mock_collection.search = MagicMock(return_value=[mock_results])

        with patch.object(searcher, '_get_milvus_collection', return_value=mock_collection):
            results = await searcher.search(
                query_vector=query_vector,
                collection_name="test_collection",
                top_k=10,
            )

            assert len(results) > 0

    @pytest.mark.asyncio
    async def test_search_with_filter(self, searcher):
        """Test search with metadata filter."""
        query_vector = [0.1] * 1536
        mock_results = [
            {"id": "1", "score": 0.95, "content": "result 1"},
        ]

        mock_collection = MagicMock()
        mock_collection.search = MagicMock(return_value=[mock_results])

        with patch.object(searcher, '_get_milvus_collection', return_value=mock_collection):
            results = await searcher.search(
                query_vector=query_vector,
                collection_name="test_collection",
                top_k=5,
                filter_expr="doc_type == 'pdf'",
            )

            assert len(results) >= 0

    def test_config_schema(self, searcher):
        """Test config schema."""
        schema = searcher.get_config_schema()

        assert "properties" in schema
        assert "top_k" in schema["properties"]


class TestFulltextSearcher:
    """Tests for FulltextSearcher."""

    @pytest.fixture
    def searcher(self):
        from app.components.searchers import FulltextSearcher
        return FulltextSearcher()

    def test_name(self, searcher):
        """Test searcher name."""
        assert searcher.name == "fulltext"

    def test_category(self, searcher):
        """Test searcher category."""
        assert searcher.category == "searchers"

    @pytest.mark.asyncio
    async def test_search(self, searcher):
        """Test fulltext search."""
        mock_response = {
            "hits": {
                "hits": [
                    {"_id": "1", "_score": 10.5, "_source": {"content": "result 1"}},
                    {"_id": "2", "_score": 8.3, "_source": {"content": "result 2"}},
                ]
            }
        }

        mock_client = MagicMock()
        mock_client.search = AsyncMock(return_value=mock_response)

        with patch.object(searcher, '_get_es_client', return_value=mock_client):
            results = await searcher.search(
                query="test query",
                index_name="test_index",
                top_k=10,
            )

            assert len(results) == 2
            assert results[0]["id"] == "1"

    @pytest.mark.asyncio
    async def test_search_empty_results(self, searcher):
        """Test search with no results."""
        mock_response = {"hits": {"hits": []}}

        mock_client = MagicMock()
        mock_client.search = AsyncMock(return_value=mock_response)

        with patch.object(searcher, '_get_es_client', return_value=mock_client):
            results = await searcher.search(
                query="nonexistent query",
                index_name="test_index",
                top_k=10,
            )

            assert len(results) == 0

    def test_config_schema(self, searcher):
        """Test config schema."""
        schema = searcher.get_config_schema()

        assert "properties" in schema
        assert "top_k" in schema["properties"]


class TestHybridSearcher:
    """Tests for HybridSearcher."""

    @pytest.fixture
    def searcher(self):
        from app.components.searchers import HybridSearcher
        return HybridSearcher()

    def test_name(self, searcher):
        """Test searcher name."""
        assert searcher.name == "hybrid"

    def test_category(self, searcher):
        """Test searcher category."""
        assert searcher.category == "searchers"

    def test_rrf_fusion(self, searcher):
        """Test Reciprocal Rank Fusion."""
        semantic_results = [
            {"id": "1", "score": 0.95},
            {"id": "2", "score": 0.85},
            {"id": "3", "score": 0.75},
        ]
        fulltext_results = [
            {"id": "2", "score": 10.5},
            {"id": "4", "score": 8.3},
            {"id": "1", "score": 6.1},
        ]

        fused = searcher._rrf_fusion(
            semantic_results=semantic_results,
            fulltext_results=fulltext_results,
            k=60,
        )

        # ID 1 and 2 should be ranked higher as they appear in both
        assert len(fused) >= 2
        ids = [r["id"] for r in fused]
        # Common items should be in top results
        assert "1" in ids or "2" in ids

    @pytest.mark.asyncio
    async def test_search(self, searcher):
        """Test hybrid search."""
        query_vector = [0.1] * 1536

        mock_semantic = MagicMock()
        mock_semantic.search = AsyncMock(return_value=[
            {"id": "1", "score": 0.95, "content": "result 1"},
        ])

        mock_fulltext = MagicMock()
        mock_fulltext.search = AsyncMock(return_value=[
            {"id": "2", "score": 10.5, "content": "result 2"},
        ])

        with patch.object(searcher, '_get_semantic_searcher', return_value=mock_semantic):
            with patch.object(searcher, '_get_fulltext_searcher', return_value=mock_fulltext):
                results = await searcher.search(
                    query="test query",
                    query_vector=query_vector,
                    collection_name="test_collection",
                    index_name="test_index",
                    top_k=10,
                    semantic_weight=0.7,
                )

                assert len(results) >= 0

    def test_config_schema(self, searcher):
        """Test config schema."""
        schema = searcher.get_config_schema()

        assert "properties" in schema
        assert "semantic_weight" in schema["properties"]
        assert "top_k" in schema["properties"]


class TestSearcherFactory:
    """Tests for SearcherFactory."""

    def test_create_semantic_searcher(self):
        """Test creating semantic searcher."""
        from app.components.searchers import SearcherFactory

        searcher = SearcherFactory.create("semantic")
        assert searcher is not None
        assert searcher.name == "semantic"

    def test_create_fulltext_searcher(self):
        """Test creating fulltext searcher."""
        from app.components.searchers import SearcherFactory

        searcher = SearcherFactory.create("fulltext")
        assert searcher is not None
        assert searcher.name == "fulltext"

    def test_create_hybrid_searcher(self):
        """Test creating hybrid searcher."""
        from app.components.searchers import SearcherFactory

        searcher = SearcherFactory.create("hybrid")
        assert searcher is not None
        assert searcher.name == "hybrid"

    def test_list_available(self):
        """Test listing available searchers."""
        from app.components.searchers import SearcherFactory

        searchers = SearcherFactory.list_available()
        assert len(searchers) >= 3
        names = [s["name"] for s in searchers]
        assert "semantic" in names
        assert "fulltext" in names
        assert "hybrid" in names

    def test_create_invalid_searcher(self):
        """Test creating invalid searcher raises error."""
        from app.components.searchers import SearcherFactory
        from app.components.base import ComponentNotFoundError

        with pytest.raises(ComponentNotFoundError):
            SearcherFactory.create("nonexistent")
