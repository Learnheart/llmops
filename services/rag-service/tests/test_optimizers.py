"""Tests for optimizer components."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestScoreThresholdOptimizer:
    """Tests for ScoreThresholdOptimizer."""

    @pytest.fixture
    def optimizer(self):
        from app.components.optimizers import ScoreThresholdOptimizer
        return ScoreThresholdOptimizer()

    def test_name(self, optimizer):
        """Test optimizer name."""
        assert optimizer.name == "score_threshold"

    def test_category(self, optimizer):
        """Test optimizer category."""
        assert optimizer.category == "optimizers"

    @pytest.mark.asyncio
    async def test_filter_by_threshold(self, optimizer):
        """Test filtering results by score threshold."""
        results = [
            {"id": "1", "score": 0.95},
            {"id": "2", "score": 0.75},
            {"id": "3", "score": 0.45},
            {"id": "4", "score": 0.30},
        ]

        filtered = await optimizer.optimize(results, threshold=0.5)

        assert len(filtered) == 2
        assert all(r["score"] >= 0.5 for r in filtered)

    @pytest.mark.asyncio
    async def test_filter_all(self, optimizer):
        """Test filtering all results."""
        results = [
            {"id": "1", "score": 0.3},
            {"id": "2", "score": 0.2},
        ]

        filtered = await optimizer.optimize(results, threshold=0.9)

        assert len(filtered) == 0

    @pytest.mark.asyncio
    async def test_filter_none(self, optimizer):
        """Test filtering no results."""
        results = [
            {"id": "1", "score": 0.95},
            {"id": "2", "score": 0.85},
        ]

        filtered = await optimizer.optimize(results, threshold=0.1)

        assert len(filtered) == 2

    def test_config_schema(self, optimizer):
        """Test config schema."""
        schema = optimizer.get_config_schema()

        assert "properties" in schema
        assert "threshold" in schema["properties"]


class TestMaxResultsOptimizer:
    """Tests for MaxResultsOptimizer."""

    @pytest.fixture
    def optimizer(self):
        from app.components.optimizers import MaxResultsOptimizer
        return MaxResultsOptimizer()

    def test_name(self, optimizer):
        """Test optimizer name."""
        assert optimizer.name == "max_results"

    def test_category(self, optimizer):
        """Test optimizer category."""
        assert optimizer.category == "optimizers"

    @pytest.mark.asyncio
    async def test_limit_results(self, optimizer):
        """Test limiting number of results."""
        results = [
            {"id": str(i), "score": 1.0 - i * 0.1}
            for i in range(10)
        ]

        limited = await optimizer.optimize(results, limit=5)

        assert len(limited) == 5

    @pytest.mark.asyncio
    async def test_limit_larger_than_results(self, optimizer):
        """Test limit larger than results."""
        results = [
            {"id": "1", "score": 0.9},
            {"id": "2", "score": 0.8},
        ]

        limited = await optimizer.optimize(results, limit=10)

        assert len(limited) == 2

    @pytest.mark.asyncio
    async def test_limit_zero(self, optimizer):
        """Test limit of zero."""
        results = [{"id": "1", "score": 0.9}]

        limited = await optimizer.optimize(results, limit=0)

        assert len(limited) == 0

    def test_config_schema(self, optimizer):
        """Test config schema."""
        schema = optimizer.get_config_schema()

        assert "properties" in schema
        assert "limit" in schema["properties"]


class TestDeduplicationOptimizer:
    """Tests for DeduplicationOptimizer."""

    @pytest.fixture
    def optimizer(self):
        from app.components.optimizers import DeduplicationOptimizer
        return DeduplicationOptimizer()

    def test_name(self, optimizer):
        """Test optimizer name."""
        assert optimizer.name == "deduplication"

    def test_category(self, optimizer):
        """Test optimizer category."""
        assert optimizer.category == "optimizers"

    @pytest.mark.asyncio
    async def test_deduplicate_by_id(self, optimizer):
        """Test deduplication by ID."""
        results = [
            {"id": "1", "score": 0.95, "content": "text 1"},
            {"id": "2", "score": 0.85, "content": "text 2"},
            {"id": "1", "score": 0.80, "content": "text 1"},  # Duplicate
            {"id": "3", "score": 0.75, "content": "text 3"},
        ]

        deduped = await optimizer.optimize(results, by="id")

        assert len(deduped) == 3
        ids = [r["id"] for r in deduped]
        assert ids.count("1") == 1

    @pytest.mark.asyncio
    async def test_deduplicate_by_content(self, optimizer):
        """Test deduplication by content similarity."""
        results = [
            {"id": "1", "score": 0.95, "content": "The quick brown fox"},
            {"id": "2", "score": 0.85, "content": "The quick brown fox jumps"},  # Similar
            {"id": "3", "score": 0.75, "content": "Something completely different"},
        ]

        deduped = await optimizer.optimize(results, by="content", similarity_threshold=0.8)

        # Should have at least 2 unique items
        assert len(deduped) >= 2

    @pytest.mark.asyncio
    async def test_keep_highest_score(self, optimizer):
        """Test keeping highest score when deduplicating."""
        results = [
            {"id": "1", "score": 0.80, "content": "text 1"},
            {"id": "1", "score": 0.95, "content": "text 1"},  # Higher score
        ]

        deduped = await optimizer.optimize(results, by="id")

        assert len(deduped) == 1
        assert deduped[0]["score"] == 0.95

    def test_config_schema(self, optimizer):
        """Test config schema."""
        schema = optimizer.get_config_schema()

        assert "properties" in schema
        assert "by" in schema["properties"]


class TestRerankingOptimizer:
    """Tests for RerankingOptimizer."""

    @pytest.fixture
    def optimizer(self):
        from app.components.optimizers import RerankingOptimizer
        return RerankingOptimizer()

    def test_name(self, optimizer):
        """Test optimizer name."""
        assert optimizer.name == "reranking"

    def test_category(self, optimizer):
        """Test optimizer category."""
        assert optimizer.category == "optimizers"

    @pytest.mark.asyncio
    async def test_rerank_with_mock_model(self, optimizer):
        """Test reranking with mocked cross-encoder."""
        results = [
            {"id": "1", "score": 0.60, "content": "Some content about cats"},
            {"id": "2", "score": 0.80, "content": "Dogs are great pets"},
            {"id": "3", "score": 0.70, "content": "Cats are wonderful"},
        ]
        query = "Tell me about cats"

        # Mock scores that would reorder results
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.9, 0.3, 0.95]  # [cats, dogs, cats wonderful]

        with patch.object(optimizer, '_get_model', return_value=mock_model):
            reranked = await optimizer.optimize(results, query=query)

            # Results should be reordered by rerank scores
            assert len(reranked) == 3
            # Item 3 (cats wonderful) should be first with score 0.95
            assert reranked[0]["id"] == "3"

    @pytest.mark.asyncio
    async def test_rerank_empty_results(self, optimizer):
        """Test reranking empty results."""
        reranked = await optimizer.optimize([], query="test")

        assert len(reranked) == 0

    @pytest.mark.asyncio
    async def test_rerank_preserves_metadata(self, optimizer):
        """Test that reranking preserves result metadata."""
        results = [
            {"id": "1", "score": 0.60, "content": "text", "metadata": {"key": "value"}},
        ]

        mock_model = MagicMock()
        mock_model.predict.return_value = [0.9]

        with patch.object(optimizer, '_get_model', return_value=mock_model):
            reranked = await optimizer.optimize(results, query="test")

            assert reranked[0]["metadata"]["key"] == "value"

    def test_config_schema(self, optimizer):
        """Test config schema."""
        schema = optimizer.get_config_schema()

        assert "properties" in schema
        assert "model" in schema["properties"]


class TestOptimizerFactory:
    """Tests for OptimizerFactory."""

    def test_create_score_threshold(self):
        """Test creating score threshold optimizer."""
        from app.components.optimizers import OptimizerFactory

        optimizer = OptimizerFactory.create("score_threshold")
        assert optimizer is not None
        assert optimizer.name == "score_threshold"

    def test_create_max_results(self):
        """Test creating max results optimizer."""
        from app.components.optimizers import OptimizerFactory

        optimizer = OptimizerFactory.create("max_results")
        assert optimizer is not None
        assert optimizer.name == "max_results"

    def test_create_deduplication(self):
        """Test creating deduplication optimizer."""
        from app.components.optimizers import OptimizerFactory

        optimizer = OptimizerFactory.create("deduplication")
        assert optimizer is not None
        assert optimizer.name == "deduplication"

    def test_create_reranking(self):
        """Test creating reranking optimizer."""
        from app.components.optimizers import OptimizerFactory

        optimizer = OptimizerFactory.create("reranking")
        assert optimizer is not None
        assert optimizer.name == "reranking"

    def test_list_available(self):
        """Test listing available optimizers."""
        from app.components.optimizers import OptimizerFactory

        optimizers = OptimizerFactory.list_available()
        assert len(optimizers) >= 4
        names = [o["name"] for o in optimizers]
        assert "score_threshold" in names
        assert "max_results" in names
        assert "deduplication" in names
        assert "reranking" in names

    def test_create_invalid_optimizer(self):
        """Test creating invalid optimizer raises error."""
        from app.components.optimizers import OptimizerFactory
        from app.components.base import ComponentNotFoundError

        with pytest.raises(ComponentNotFoundError):
            OptimizerFactory.create("nonexistent")


class TestOptimizerChain:
    """Tests for chaining multiple optimizers."""

    @pytest.mark.asyncio
    async def test_chain_optimizers(self):
        """Test chaining multiple optimizers."""
        from app.components.optimizers import (
            ScoreThresholdOptimizer,
            MaxResultsOptimizer,
            DeduplicationOptimizer,
        )

        results = [
            {"id": "1", "score": 0.95},
            {"id": "2", "score": 0.85},
            {"id": "1", "score": 0.80},  # Duplicate
            {"id": "3", "score": 0.45},  # Below threshold
            {"id": "4", "score": 0.75},
            {"id": "5", "score": 0.65},
        ]

        # Chain: threshold -> dedup -> max results
        threshold_opt = ScoreThresholdOptimizer()
        dedup_opt = DeduplicationOptimizer()
        max_opt = MaxResultsOptimizer()

        # Apply threshold (0.5)
        filtered = await threshold_opt.optimize(results, threshold=0.5)
        assert len(filtered) == 5  # id 3 removed

        # Apply dedup
        deduped = await dedup_opt.optimize(filtered, by="id")
        assert len(deduped) == 4  # duplicate id 1 removed

        # Apply max results
        final = await max_opt.optimize(deduped, limit=3)
        assert len(final) == 3
