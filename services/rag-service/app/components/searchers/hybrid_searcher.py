"""Hybrid searcher combining semantic and full-text search."""

from typing import Any, Dict, List, Optional

from app.components.searchers.base import BaseSearcher, SearchResult
from app.components.searchers.factory import SearcherFactory
from app.components.searchers.semantic_searcher import SemanticSearcher
from app.components.searchers.fulltext_searcher import FulltextSearcher
from app.config import get_settings


class HybridSearcher(BaseSearcher):
    """Searcher combining semantic and full-text search using RRF.

    Uses Reciprocal Rank Fusion (RRF) to combine results from
    vector search (Milvus) and full-text search (Elasticsearch).
    """

    name: str = "hybrid"
    description: str = "Combines semantic and full-text search using Reciprocal Rank Fusion"

    def __init__(self):
        """Initialize hybrid searcher."""
        super().__init__()
        self._semantic_searcher = None
        self._fulltext_searcher = None

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "collection_name": {
                    "type": "string",
                    "description": "Collection/index to search",
                },
                "top_k": {
                    "type": "integer",
                    "default": 10,
                    "description": "Number of results to return",
                },
                "semantic_weight": {
                    "type": "number",
                    "default": 0.7,
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Weight for semantic search (1 - this = fulltext weight)",
                },
                "rrf_k": {
                    "type": "integer",
                    "default": 60,
                    "description": "RRF constant (higher = smoother ranking)",
                },
                "fetch_multiplier": {
                    "type": "number",
                    "default": 2.0,
                    "description": "Fetch multiplier for each searcher",
                },
            },
            "required": ["collection_name"],
        }

    @property
    def semantic_searcher(self) -> SemanticSearcher:
        """Get semantic searcher instance."""
        if self._semantic_searcher is None:
            self._semantic_searcher = SemanticSearcher()
        return self._semantic_searcher

    @property
    def fulltext_searcher(self) -> FulltextSearcher:
        """Get fulltext searcher instance."""
        if self._fulltext_searcher is None:
            self._fulltext_searcher = FulltextSearcher()
        return self._fulltext_searcher

    async def search(
        self,
        query: str,
        collection_name: str,
        top_k: int = 10,
        query_vector: Optional[List[float]] = None,
        embedder=None,
        semantic_weight: float = 0.7,
        rrf_k: int = 60,
        fetch_multiplier: float = 2.0,
        **kwargs,
    ) -> List[SearchResult]:
        """Perform hybrid search with RRF fusion.

        Args:
            query: Search query text
            collection_name: Collection to search
            top_k: Number of results
            query_vector: Pre-computed query embedding
            embedder: Embedder for query embedding
            semantic_weight: Weight for semantic results
            rrf_k: RRF constant
            fetch_multiplier: How many more results to fetch

        Returns:
            List of SearchResult objects
        """
        # Calculate fetch count
        fetch_k = int(top_k * fetch_multiplier)

        # Perform both searches
        import asyncio

        # Get semantic results
        semantic_task = self.semantic_searcher.search(
            query=query,
            collection_name=collection_name,
            top_k=fetch_k,
            query_vector=query_vector,
            embedder=embedder,
            **kwargs,
        )

        # Get fulltext results
        fulltext_task = self.fulltext_searcher.search(
            query=query,
            collection_name=collection_name,
            top_k=fetch_k,
            **kwargs,
        )

        # Run in parallel
        try:
            semantic_results, fulltext_results = await asyncio.gather(
                semantic_task,
                fulltext_task,
                return_exceptions=True,
            )
        except Exception as e:
            # If one fails, try to use the other
            semantic_results = []
            fulltext_results = []

        # Handle exceptions
        if isinstance(semantic_results, Exception):
            semantic_results = []
        if isinstance(fulltext_results, Exception):
            fulltext_results = []

        # Apply RRF fusion
        fused_results = self._rrf_fusion(
            semantic_results=semantic_results,
            fulltext_results=fulltext_results,
            semantic_weight=semantic_weight,
            k=rrf_k,
        )

        # Return top_k
        return fused_results[:top_k]

    def _rrf_fusion(
        self,
        semantic_results: List[SearchResult],
        fulltext_results: List[SearchResult],
        semantic_weight: float,
        k: int,
    ) -> List[SearchResult]:
        """Apply Reciprocal Rank Fusion to combine results.

        RRF Score = Σ weight_i / (k + rank_i)

        Args:
            semantic_results: Results from semantic search
            fulltext_results: Results from fulltext search
            semantic_weight: Weight for semantic results
            k: RRF constant

        Returns:
            Fused and sorted results
        """
        fulltext_weight = 1.0 - semantic_weight
        scores: Dict[str, float] = {}
        contents: Dict[str, str] = {}
        metadatas: Dict[str, Dict] = {}

        # Add semantic scores
        for rank, result in enumerate(semantic_results, 1):
            rrf_score = semantic_weight / (k + rank)
            scores[result.id] = scores.get(result.id, 0) + rrf_score
            contents[result.id] = result.content
            metadatas[result.id] = result.metadata

        # Add fulltext scores
        for rank, result in enumerate(fulltext_results, 1):
            rrf_score = fulltext_weight / (k + rank)
            scores[result.id] = scores.get(result.id, 0) + rrf_score
            # Keep content/metadata from first occurrence
            if result.id not in contents:
                contents[result.id] = result.content
                metadatas[result.id] = result.metadata

        # Sort by combined score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        # Build result list
        results = []
        max_score = max(scores.values()) if scores else 1.0

        for doc_id in sorted_ids:
            # Normalize to 0-1
            normalized_score = scores[doc_id] / max_score if max_score > 0 else 0

            results.append(
                SearchResult(
                    id=doc_id,
                    content=contents.get(doc_id, ""),
                    score=normalized_score,
                    metadata=metadatas.get(doc_id, {}),
                )
            )

        return results


# Register with factory
SearcherFactory.register("hybrid", HybridSearcher)
