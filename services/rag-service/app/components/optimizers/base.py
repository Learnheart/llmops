"""Base optimizer class for search result optimization."""

from abc import abstractmethod
from typing import Any, Dict, List, Optional

from app.components.base.component import BaseComponent
from app.components.searchers.base import SearchResult


class BaseOptimizer(BaseComponent):
    """Abstract base class for search result optimizers.

    Optimizers post-process search results to improve quality,
    filter, rerank, or deduplicate results.
    """

    category: str = "optimizers"

    # Execution order (lower = earlier)
    order: int = 50

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Return configuration schema for optimizer."""
        return {
            "type": "object",
            "properties": {},
        }

    @abstractmethod
    async def optimize(
        self,
        results: List[SearchResult],
        query: Optional[str] = None,
        **kwargs,
    ) -> List[SearchResult]:
        """Optimize search results.

        Args:
            results: List of search results to optimize
            query: Original search query (if needed)
            **kwargs: Additional optimizer-specific options

        Returns:
            Optimized list of SearchResult objects
        """
        pass

    async def process(
        self,
        input_data: Any,
        config: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Process method implementing BaseComponent interface.

        Args:
            input_data: List of SearchResult objects
            config: Optimizer configuration

        Returns:
            Optimized list of SearchResult objects
        """
        if not isinstance(input_data, list):
            raise ValueError("Input must be a list of SearchResult objects")

        config = config or {}
        return await self.optimize(input_data, **config)

    def to_dict(self) -> Dict[str, Any]:
        """Convert component metadata to dictionary."""
        result = super().to_dict()
        result["order"] = self.order
        return result
