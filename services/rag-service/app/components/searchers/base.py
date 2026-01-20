"""Base searcher class for document retrieval."""

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.components.base.component import BaseComponent


@dataclass
class SearchResult:
    """A single search result."""

    id: str
    """Document/chunk ID."""

    content: str
    """Text content."""

    score: float
    """Relevance score (higher is better, normalized to 0-1 when possible)."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "score": self.score,
            "metadata": self.metadata,
        }


class BaseSearcher(BaseComponent):
    """Abstract base class for search components.

    Searchers retrieve relevant documents based on a query.
    """

    category: str = "searchers"

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Return configuration schema for searcher."""
        return {
            "type": "object",
            "properties": {
                "collection_name": {
                    "type": "string",
                    "description": "Name of the collection to search",
                },
                "top_k": {
                    "type": "integer",
                    "default": 10,
                    "description": "Number of results to return",
                    "minimum": 1,
                    "maximum": 1000,
                },
            },
            "required": ["collection_name"],
        }

    @abstractmethod
    async def search(
        self,
        query: str,
        collection_name: str,
        top_k: int = 10,
        **kwargs,
    ) -> List[SearchResult]:
        """Search for relevant documents.

        Args:
            query: Search query text
            collection_name: Collection to search in
            top_k: Number of results to return
            **kwargs: Additional search options

        Returns:
            List of SearchResult objects
        """
        pass

    async def process(
        self,
        input_data: Any,
        config: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Process method implementing BaseComponent interface.

        Args:
            input_data: Query string
            config: Search configuration

        Returns:
            List of SearchResult objects
        """
        if not isinstance(input_data, str):
            raise ValueError("Input must be a query string")

        config = config or {}
        collection_name = config.get("collection_name")

        if not collection_name:
            raise ValueError("collection_name is required in config")

        return await self.search(input_data, collection_name, **config)
