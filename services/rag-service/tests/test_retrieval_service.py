"""Tests for RetrievalService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.models.schemas import (
    RetrievalPipelineConfig,
    EmbedderConfig,
    SearcherConfig,
    OptimizerConfig,
)


class TestRetrievalService:
    """Tests for RetrievalService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def mock_embedder(self):
        """Create mock embedder."""
        embedder = MagicMock()
        embedder.embed_single = AsyncMock(return_value=[0.1] * 1536)
        return embedder

    @pytest.fixture
    def mock_searcher(self):
        """Create mock searcher."""
        searcher = MagicMock()

        # Create search results
        result1 = MagicMock()
        result1.id = "chunk-1"
        result1.content = "First result content"
        result1.score = 0.95
        result1.metadata = {"document_id": "doc-1"}

        result2 = MagicMock()
        result2.id = "chunk-2"
        result2.content = "Second result content"
        result2.score = 0.85
        result2.metadata = {"document_id": "doc-1"}

        searcher.search = AsyncMock(return_value=[result1, result2])
        return searcher

    @pytest.fixture
    def mock_optimizer(self):
        """Create mock optimizer."""
        optimizer = MagicMock()
        # Optimizer returns filtered results
        optimizer.optimize = AsyncMock(side_effect=lambda results, **kwargs: results)
        return optimizer

    @pytest.fixture
    def retrieval_config(self):
        """Create sample retrieval config."""
        return RetrievalPipelineConfig(
            embedder=EmbedderConfig(type="openai"),
            searcher=SearcherConfig(type="hybrid", semantic_weight=0.7),
            optimizers=[],
        )

    @pytest.fixture
    def retrieval_config_with_optimizers(self):
        """Create retrieval config with optimizers."""
        return RetrievalPipelineConfig(
            embedder=EmbedderConfig(type="openai"),
            searcher=SearcherConfig(type="hybrid"),
            optimizers=[
                OptimizerConfig(type="score_threshold", threshold=0.5),
                OptimizerConfig(type="max_results", limit=5),
            ],
        )

    @pytest.mark.asyncio
    async def test_retrieve_basic(
        self,
        mock_db,
        mock_embedder,
        mock_searcher,
        retrieval_config,
    ):
        """Test basic retrieval."""
        # Setup mock db results for enrichment
        mock_chunk = MagicMock()
        mock_chunk.id = "chunk-1"
        mock_chunk.document_id = "doc-1"
        mock_chunk.chunk_index = 0
        mock_chunk.metadata = {}

        mock_doc = MagicMock()
        mock_doc.id = "doc-1"
        mock_doc.filename = "test.pdf"

        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_chunk])))),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_doc])))),
        ])

        with patch("app.services.retrieval_service.EmbedderFactory") as embedder_factory, \
             patch("app.services.retrieval_service.SearcherFactory") as searcher_factory:

            embedder_factory.create.return_value = mock_embedder
            searcher_factory.create.return_value = mock_searcher

            from app.services.retrieval_service import RetrievalService

            service = RetrievalService(mock_db)

            result = await service.retrieve(
                user_id="user123",
                knowledge_base_id="kb123",
                query="test query",
                config=retrieval_config,
                top_k=5,
            )

            assert result.query == "test query"
            assert result.total_results > 0
            assert result.run_id is not None

    @pytest.mark.asyncio
    async def test_retrieve_with_optimizers(
        self,
        mock_db,
        mock_embedder,
        mock_searcher,
        mock_optimizer,
        retrieval_config_with_optimizers,
    ):
        """Test retrieval with optimizer chain."""
        # Setup mock db results
        mock_chunk = MagicMock()
        mock_chunk.id = "chunk-1"
        mock_chunk.document_id = "doc-1"
        mock_chunk.chunk_index = 0
        mock_chunk.metadata = {}

        mock_doc = MagicMock()
        mock_doc.id = "doc-1"
        mock_doc.filename = "test.pdf"

        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_chunk])))),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_doc])))),
        ])

        with patch("app.services.retrieval_service.EmbedderFactory") as embedder_factory, \
             patch("app.services.retrieval_service.SearcherFactory") as searcher_factory, \
             patch("app.services.retrieval_service.OptimizerFactory") as optimizer_factory:

            embedder_factory.create.return_value = mock_embedder
            searcher_factory.create.return_value = mock_searcher
            optimizer_factory.create.return_value = mock_optimizer

            from app.services.retrieval_service import RetrievalService

            service = RetrievalService(mock_db)

            result = await service.retrieve(
                user_id="user123",
                knowledge_base_id="kb123",
                query="test query",
                config=retrieval_config_with_optimizers,
                top_k=5,
            )

            # Verify optimizers were called
            assert optimizer_factory.create.call_count == 2
            assert result.run_id is not None

    @pytest.mark.asyncio
    async def test_retrieve_creates_pipeline_run(
        self,
        mock_db,
        mock_embedder,
        mock_searcher,
        retrieval_config,
    ):
        """Test that retrieval creates a pipeline run record."""
        # Setup empty results for simplicity
        mock_searcher.search = AsyncMock(return_value=[])

        with patch("app.services.retrieval_service.EmbedderFactory") as embedder_factory, \
             patch("app.services.retrieval_service.SearcherFactory") as searcher_factory:

            embedder_factory.create.return_value = mock_embedder
            searcher_factory.create.return_value = mock_searcher

            from app.services.retrieval_service import RetrievalService

            service = RetrievalService(mock_db)

            result = await service.retrieve(
                user_id="user123",
                knowledge_base_id="kb123",
                query="test query",
                config=retrieval_config,
                top_k=5,
            )

            # Verify db operations
            assert mock_db.add.called
            assert mock_db.commit.called
            assert result.run_id is not None

    @pytest.mark.asyncio
    async def test_retrieve_with_error(
        self,
        mock_db,
        retrieval_config,
    ):
        """Test retrieval handles errors properly."""
        with patch("app.services.retrieval_service.EmbedderFactory") as embedder_factory:
            # Make embedder raise an exception
            mock_embedder = MagicMock()
            mock_embedder.embed_single = AsyncMock(side_effect=Exception("Embedding error"))
            embedder_factory.create.return_value = mock_embedder

            from app.services.retrieval_service import RetrievalService

            service = RetrievalService(mock_db)

            with pytest.raises(Exception) as exc_info:
                await service.retrieve(
                    user_id="user123",
                    knowledge_base_id="kb123",
                    query="test query",
                    config=retrieval_config,
                    top_k=5,
                )

            assert "Embedding error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_retrieve_empty_results(
        self,
        mock_db,
        mock_embedder,
        retrieval_config,
    ):
        """Test retrieval with no results."""
        mock_searcher = MagicMock()
        mock_searcher.search = AsyncMock(return_value=[])

        with patch("app.services.retrieval_service.EmbedderFactory") as embedder_factory, \
             patch("app.services.retrieval_service.SearcherFactory") as searcher_factory:

            embedder_factory.create.return_value = mock_embedder
            searcher_factory.create.return_value = mock_searcher

            from app.services.retrieval_service import RetrievalService

            service = RetrievalService(mock_db)

            result = await service.retrieve(
                user_id="user123",
                knowledge_base_id="kb123",
                query="nonexistent query",
                config=retrieval_config,
                top_k=5,
            )

            assert result.total_results == 0
            assert len(result.results) == 0

    @pytest.mark.asyncio
    async def test_retrieve_respects_top_k(
        self,
        mock_db,
        mock_embedder,
        retrieval_config,
    ):
        """Test that top_k limits results."""
        # Create 10 search results
        mock_results = []
        for i in range(10):
            result = MagicMock()
            result.id = f"chunk-{i}"
            result.content = f"Result {i}"
            result.score = 0.9 - (i * 0.05)
            result.metadata = {}
            mock_results.append(result)

        mock_searcher = MagicMock()
        mock_searcher.search = AsyncMock(return_value=mock_results)

        # Setup mock db results
        mock_chunks = []
        for i in range(10):
            chunk = MagicMock()
            chunk.id = f"chunk-{i}"
            chunk.document_id = "doc-1"
            chunk.chunk_index = i
            chunk.metadata = {}
            mock_chunks.append(chunk)

        mock_doc = MagicMock()
        mock_doc.id = "doc-1"
        mock_doc.filename = "test.pdf"

        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=mock_chunks[:3])))),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_doc])))),
        ])

        with patch("app.services.retrieval_service.EmbedderFactory") as embedder_factory, \
             patch("app.services.retrieval_service.SearcherFactory") as searcher_factory:

            embedder_factory.create.return_value = mock_embedder
            searcher_factory.create.return_value = mock_searcher

            from app.services.retrieval_service import RetrievalService

            service = RetrievalService(mock_db)

            result = await service.retrieve(
                user_id="user123",
                knowledge_base_id="kb123",
                query="test query",
                config=retrieval_config,
                top_k=3,
            )

            # Should be limited to top_k
            assert len(result.results) <= 3

    @pytest.mark.asyncio
    async def test_retrieve_metrics_calculation(
        self,
        mock_db,
        mock_embedder,
        mock_searcher,
        retrieval_config,
    ):
        """Test that metrics are calculated."""
        mock_searcher.search = AsyncMock(return_value=[])

        with patch("app.services.retrieval_service.EmbedderFactory") as embedder_factory, \
             patch("app.services.retrieval_service.SearcherFactory") as searcher_factory:

            embedder_factory.create.return_value = mock_embedder
            searcher_factory.create.return_value = mock_searcher

            from app.services.retrieval_service import RetrievalService

            service = RetrievalService(mock_db)

            result = await service.retrieve(
                user_id="user123",
                knowledge_base_id="kb123",
                query="test query",
                config=retrieval_config,
                top_k=5,
            )

            # Verify metrics are present
            assert "duration_ms" in result.metrics
            assert "embed_time_ms" in result.metrics
            assert "search_time_ms" in result.metrics
            assert "optimize_time_ms" in result.metrics
            assert result.metrics["duration_ms"] >= 0


class TestRetrievalServiceEnrichResults:
    """Tests for _enrich_results helper method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_enrich_empty_results(self, mock_db):
        """Test enriching empty results."""
        from app.services.retrieval_service import RetrievalService

        service = RetrievalService(mock_db)

        result = await service._enrich_results([])

        assert result == []

    @pytest.mark.asyncio
    async def test_enrich_with_valid_results(self, mock_db):
        """Test enriching valid results."""
        # Create mock search results
        search_result = MagicMock()
        search_result.id = "chunk-1"
        search_result.content = "Test content"
        search_result.score = 0.95
        search_result.metadata = {"key": "value"}

        # Create mock chunk
        mock_chunk = MagicMock()
        mock_chunk.id = "chunk-1"
        mock_chunk.document_id = "doc-1"
        mock_chunk.chunk_index = 0
        mock_chunk.metadata = {"chunk_key": "chunk_value"}

        # Create mock document
        mock_doc = MagicMock()
        mock_doc.id = "doc-1"
        mock_doc.filename = "test.pdf"

        # Setup db mock
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_chunk])))),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_doc])))),
        ])

        from app.services.retrieval_service import RetrievalService

        service = RetrievalService(mock_db)

        results = await service._enrich_results([search_result])

        assert len(results) == 1
        assert results[0].id == "chunk-1"
        assert results[0].content == "Test content"
        assert results[0].score == 0.95
        assert results[0].document_id == "doc-1"
        assert results[0].document_filename == "test.pdf"
        assert results[0].chunk_index == 0

    @pytest.mark.asyncio
    async def test_enrich_preserves_order(self, mock_db):
        """Test that enrichment preserves result order."""
        # Create mock search results
        search_results = []
        mock_chunks = []
        for i in range(3):
            result = MagicMock()
            result.id = f"chunk-{i}"
            result.content = f"Content {i}"
            result.score = 0.9 - (i * 0.1)
            result.metadata = {}
            search_results.append(result)

            chunk = MagicMock()
            chunk.id = f"chunk-{i}"
            chunk.document_id = "doc-1"
            chunk.chunk_index = i
            chunk.metadata = {}
            mock_chunks.append(chunk)

        mock_doc = MagicMock()
        mock_doc.id = "doc-1"
        mock_doc.filename = "test.pdf"

        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=mock_chunks)))),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_doc])))),
        ])

        from app.services.retrieval_service import RetrievalService

        service = RetrievalService(mock_db)

        results = await service._enrich_results(search_results)

        # Verify order is preserved
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.id == f"chunk-{i}"


class TestRetrievalServiceIntegration:
    """Integration-style tests for RetrievalService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        return db

    @pytest.mark.asyncio
    async def test_full_retrieval_pipeline(self, mock_db):
        """Test the full retrieval pipeline flow."""
        with patch("app.services.retrieval_service.EmbedderFactory") as embedder_factory, \
             patch("app.services.retrieval_service.SearcherFactory") as searcher_factory, \
             patch("app.services.retrieval_service.OptimizerFactory") as optimizer_factory:

            # Setup embedder
            mock_embedder = MagicMock()
            mock_embedder.embed_single = AsyncMock(return_value=[0.1] * 1536)
            embedder_factory.create.return_value = mock_embedder

            # Setup searcher
            search_result = MagicMock()
            search_result.id = "chunk-1"
            search_result.content = "Found content"
            search_result.score = 0.9
            search_result.metadata = {}

            mock_searcher = MagicMock()
            mock_searcher.search = AsyncMock(return_value=[search_result])
            searcher_factory.create.return_value = mock_searcher

            # Setup optimizer
            mock_optimizer = MagicMock()
            mock_optimizer.optimize = AsyncMock(side_effect=lambda results, **kwargs: results)
            optimizer_factory.create.return_value = mock_optimizer

            # Setup db results
            mock_chunk = MagicMock()
            mock_chunk.id = "chunk-1"
            mock_chunk.document_id = "doc-1"
            mock_chunk.chunk_index = 0
            mock_chunk.metadata = {}

            mock_doc = MagicMock()
            mock_doc.id = "doc-1"
            mock_doc.filename = "test.pdf"

            mock_db.execute = AsyncMock(side_effect=[
                MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_chunk])))),
                MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_doc])))),
            ])

            from app.services.retrieval_service import RetrievalService

            service = RetrievalService(mock_db)

            config = RetrievalPipelineConfig(
                embedder=EmbedderConfig(type="openai"),
                searcher=SearcherConfig(type="hybrid"),
                optimizers=[OptimizerConfig(type="score_threshold", threshold=0.5)],
            )

            result = await service.retrieve(
                user_id="user1",
                knowledge_base_id="kb1",
                query="test query",
                config=config,
                top_k=5,
            )

            # Verify execution order
            mock_embedder.embed_single.assert_called_once_with("test query")
            mock_searcher.search.assert_called_once()
            mock_optimizer.optimize.assert_called_once()

            # Verify result
            assert result.query == "test query"
            assert result.total_results == 1
            assert result.results[0].content == "Found content"

    @pytest.mark.asyncio
    async def test_fetch_size_with_optimizers(self, mock_db):
        """Test that fetch size is increased when optimizers are present."""
        with patch("app.services.retrieval_service.EmbedderFactory") as embedder_factory, \
             patch("app.services.retrieval_service.SearcherFactory") as searcher_factory, \
             patch("app.services.retrieval_service.OptimizerFactory") as optimizer_factory:

            mock_embedder = MagicMock()
            mock_embedder.embed_single = AsyncMock(return_value=[0.1] * 1536)
            embedder_factory.create.return_value = mock_embedder

            mock_searcher = MagicMock()
            mock_searcher.search = AsyncMock(return_value=[])
            searcher_factory.create.return_value = mock_searcher

            mock_optimizer = MagicMock()
            mock_optimizer.optimize = AsyncMock(return_value=[])
            optimizer_factory.create.return_value = mock_optimizer

            from app.services.retrieval_service import RetrievalService

            service = RetrievalService(mock_db)

            config = RetrievalPipelineConfig(
                embedder=EmbedderConfig(type="openai"),
                searcher=SearcherConfig(type="hybrid"),
                optimizers=[OptimizerConfig(type="score_threshold", threshold=0.5)],
            )

            await service.retrieve(
                user_id="user1",
                knowledge_base_id="kb1",
                query="test",
                config=config,
                top_k=5,
            )

            # When optimizers are present, fetch_k should be top_k * 3
            call_kwargs = mock_searcher.search.call_args.kwargs
            assert call_kwargs["top_k"] == 15  # 5 * 3

    @pytest.mark.asyncio
    async def test_collection_name_generation(self, mock_db):
        """Test collection name is generated correctly."""
        with patch("app.services.retrieval_service.EmbedderFactory") as embedder_factory, \
             patch("app.services.retrieval_service.SearcherFactory") as searcher_factory:

            mock_embedder = MagicMock()
            mock_embedder.embed_single = AsyncMock(return_value=[0.1] * 1536)
            embedder_factory.create.return_value = mock_embedder

            mock_searcher = MagicMock()
            mock_searcher.search = AsyncMock(return_value=[])
            searcher_factory.create.return_value = mock_searcher

            from app.services.retrieval_service import RetrievalService

            service = RetrievalService(mock_db)

            config = RetrievalPipelineConfig()

            await service.retrieve(
                user_id="user123",
                knowledge_base_id="kb456",
                query="test",
                config=config,
                top_k=5,
            )

            # Verify collection name
            call_kwargs = mock_searcher.search.call_args.kwargs
            assert call_kwargs["collection_name"] == "kb_user123_kb456"
