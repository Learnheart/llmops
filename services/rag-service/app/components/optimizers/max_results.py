"""Max results optimizer."""

from typing import Any, Dict, List, Optional

from app.components.optimizers.base import BaseOptimizer
from app.components.optimizers.factory import OptimizerFactory
from app.components.searchers.base import SearchResult


class MaxResultsOptimizer(BaseOptimizer):
    """Optimizer that limits the number of results.

    Returns only the top N results, typically used as the
    final optimizer in a chain.
    """

    name: str = "max_results"
    description: str = "Limits the number of results returned"
    order: int = 100  # Run last

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Maximum number of results to return",
                },
            },
        }

    async def optimize(
        self,
        results: List[SearchResult],
        query: Optional[str] = None,
        limit: int = 5,
        **kwargs,
    ) -> List[SearchResult]:
        """Limit number of results.

        Args:
            results: Search results to limit
            query: Original query (not used)
            limit: Maximum results to return

        Returns:
            Limited results
        """
        return results[:limit]


# Register with factory
OptimizerFactory.register("max_results", MaxResultsOptimizer)
