"""Deduplication optimizer."""

from typing import Any, Dict, List, Optional

from app.components.optimizers.base import BaseOptimizer
from app.components.optimizers.factory import OptimizerFactory
from app.components.searchers.base import SearchResult


class DeduplicationOptimizer(BaseOptimizer):
    """Optimizer that removes duplicate or near-duplicate results.

    Uses content similarity to identify and remove duplicates,
    keeping the highest-scored version.
    """

    name: str = "deduplication"
    description: str = "Removes duplicate or near-duplicate results"
    order: int = 30

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "similarity_threshold": {
                    "type": "number",
                    "default": 0.9,
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Similarity threshold for considering duplicates",
                },
                "method": {
                    "type": "string",
                    "enum": ["exact", "jaccard", "overlap"],
                    "default": "jaccard",
                    "description": "Method for comparing content",
                },
            },
        }

    async def optimize(
        self,
        results: List[SearchResult],
        query: Optional[str] = None,
        similarity_threshold: float = 0.9,
        method: str = "jaccard",
        **kwargs,
    ) -> List[SearchResult]:
        """Remove duplicate results.

        Args:
            results: Search results to deduplicate
            query: Original query (not used)
            similarity_threshold: Threshold for duplicate detection
            method: Comparison method

        Returns:
            Deduplicated results
        """
        if not results:
            return results

        # Results are assumed to be sorted by score (highest first)
        unique_results = []
        seen_contents = []

        for result in results:
            is_duplicate = False

            for seen_content in seen_contents:
                similarity = self._calculate_similarity(
                    result.content,
                    seen_content,
                    method,
                )

                if similarity >= similarity_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_results.append(result)
                seen_contents.append(result.content)

        return unique_results

    def _calculate_similarity(
        self,
        text1: str,
        text2: str,
        method: str,
    ) -> float:
        """Calculate similarity between two texts.

        Args:
            text1: First text
            text2: Second text
            method: Comparison method

        Returns:
            Similarity score (0-1)
        """
        if method == "exact":
            return 1.0 if text1.strip() == text2.strip() else 0.0

        # Tokenize
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        if method == "jaccard":
            intersection = len(words1 & words2)
            union = len(words1 | words2)
            return intersection / union if union > 0 else 0.0

        elif method == "overlap":
            intersection = len(words1 & words2)
            min_size = min(len(words1), len(words2))
            return intersection / min_size if min_size > 0 else 0.0

        return 0.0


# Register with factory
OptimizerFactory.register("deduplication", DeduplicationOptimizer)
