"""Score threshold optimizer."""

from typing import Any, Dict, List, Optional

from app.components.optimizers.base import BaseOptimizer
from app.components.optimizers.factory import OptimizerFactory
from app.components.searchers.base import SearchResult


class ScoreThresholdOptimizer(BaseOptimizer):
    """Optimizer that filters results below a score threshold.

    Removes results with scores below the specified minimum threshold.
    """

    name: str = "score_threshold"
    description: str = "Filters out results with scores below a threshold"
    order: int = 20

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "threshold": {
                    "type": "number",
                    "default": 0.5,
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Minimum score threshold (0-1)",
                },
            },
        }

    async def optimize(
        self,
        results: List[SearchResult],
        query: Optional[str] = None,
        threshold: float = 0.5,
        **kwargs,
    ) -> List[SearchResult]:
        """Filter results by score threshold.

        Args:
            results: Search results to filter
            query: Original query (not used)
            threshold: Minimum score threshold

        Returns:
            Filtered results
        """
        return [r for r in results if r.score >= threshold]


# Register with factory
OptimizerFactory.register("score_threshold", ScoreThresholdOptimizer)
