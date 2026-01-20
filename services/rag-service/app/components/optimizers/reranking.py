"""Reranking optimizer using cross-encoder models."""

from typing import Any, Dict, List, Optional

from app.components.optimizers.base import BaseOptimizer
from app.components.optimizers.factory import OptimizerFactory
from app.components.searchers.base import SearchResult


class RerankingOptimizer(BaseOptimizer):
    """Optimizer that reranks results using a cross-encoder model.

    Cross-encoders process query and document together,
    providing more accurate relevance scores than bi-encoders.
    """

    name: str = "reranking"
    description: str = "Reranks results using a cross-encoder model for better accuracy"
    order: int = 10  # Run early to benefit other optimizers

    # Available models
    MODELS = [
        "cross-encoder/ms-marco-MiniLM-L-6-v2",
        "cross-encoder/ms-marco-MiniLM-L-12-v2",
        "cross-encoder/ms-marco-TinyBERT-L-2-v2",
    ]

    DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def __init__(self, model: Optional[str] = None):
        """Initialize reranking optimizer.

        Args:
            model: Cross-encoder model name
        """
        super().__init__()
        self.model_name = model or self.DEFAULT_MODEL
        self._model = None

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "default": cls.DEFAULT_MODEL,
                    "description": "Cross-encoder model for reranking",
                },
                "top_k": {
                    "type": "integer",
                    "default": 10,
                    "description": "Number of top results to rerank",
                    "minimum": 1,
                },
                "batch_size": {
                    "type": "integer",
                    "default": 32,
                    "description": "Batch size for inference",
                },
            },
        }

    @property
    def model(self):
        """Lazy-load cross-encoder model."""
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required for reranking. "
                    "Install with: pip install sentence-transformers"
                )

            self._model = CrossEncoder(self.model_name)

        return self._model

    async def optimize(
        self,
        results: List[SearchResult],
        query: Optional[str] = None,
        model: Optional[str] = None,
        top_k: int = 10,
        batch_size: int = 32,
        **kwargs,
    ) -> List[SearchResult]:
        """Rerank results using cross-encoder.

        Args:
            results: Search results to rerank
            query: Original search query (required)
            model: Model to use (overrides default)
            top_k: Number of results to rerank
            batch_size: Batch size for inference

        Returns:
            Reranked results
        """
        if not query:
            # Cannot rerank without query
            return results

        if not results:
            return results

        # Only rerank top_k results
        to_rerank = results[:top_k]
        remaining = results[top_k:]

        # Reload model if different
        if model and model != self.model_name:
            self.model_name = model
            self._model = None

        # Prepare pairs for cross-encoder
        pairs = [(query, r.content) for r in to_rerank]

        # Get reranking scores
        scores = self.model.predict(pairs, batch_size=batch_size, show_progress_bar=False)

        # Normalize scores to 0-1 using sigmoid
        import numpy as np
        normalized_scores = 1 / (1 + np.exp(-np.array(scores)))

        # Update scores and sort
        reranked = []
        for result, new_score in zip(to_rerank, normalized_scores):
            reranked.append(
                SearchResult(
                    id=result.id,
                    content=result.content,
                    score=float(new_score),
                    metadata={
                        **result.metadata,
                        "original_score": result.score,
                        "reranked": True,
                    },
                )
            )

        # Sort by new scores
        reranked.sort(key=lambda x: x.score, reverse=True)

        # Combine with remaining results
        return reranked + remaining


# Register with factory
OptimizerFactory.register("reranking", RerankingOptimizer)
