"""Base indexer class for vector storage."""

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.components.base.component import BaseComponent


@dataclass
class IndexedDocument:
    """Document to be indexed."""

    id: str
    """Unique identifier for the document."""

    content: str
    """Text content of the document."""

    vector: List[float]
    """Embedding vector."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""


class BaseIndexer(BaseComponent):
    """Abstract base class for vector indexers.

    Indexers store document embeddings for efficient similarity search.
    """

    category: str = "indexers"

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Return configuration schema for indexer."""
        return {
            "type": "object",
            "properties": {
                "collection_name": {
                    "type": "string",
                    "description": "Name of the collection/index to use",
                },
                "dimension": {
                    "type": "integer",
                    "description": "Dimension of embedding vectors",
                },
            },
            "required": ["collection_name"],
        }

    @abstractmethod
    async def create_collection(
        self,
        collection_name: str,
        dimension: int,
        **kwargs,
    ) -> bool:
        """Create a new collection/index.

        Args:
            collection_name: Name for the collection
            dimension: Embedding vector dimension
            **kwargs: Additional collection options

        Returns:
            True if created successfully
        """
        pass

    @abstractmethod
    async def index(
        self,
        documents: List[IndexedDocument],
        collection_name: str,
        **kwargs,
    ) -> List[str]:
        """Index documents with their embeddings.

        Args:
            documents: List of documents to index
            collection_name: Target collection name
            **kwargs: Additional indexing options

        Returns:
            List of indexed document IDs
        """
        pass

    @abstractmethod
    async def delete(
        self,
        ids: List[str],
        collection_name: str,
        **kwargs,
    ) -> int:
        """Delete documents by IDs.

        Args:
            ids: List of document IDs to delete
            collection_name: Collection to delete from
            **kwargs: Additional options

        Returns:
            Number of documents deleted
        """
        pass

    @abstractmethod
    async def collection_exists(self, collection_name: str) -> bool:
        """Check if a collection exists.

        Args:
            collection_name: Name of the collection

        Returns:
            True if collection exists
        """
        pass

    async def process(
        self,
        input_data: Any,
        config: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Process method implementing BaseComponent interface.

        Args:
            input_data: List of IndexedDocument objects
            config: Indexer configuration (must include collection_name)

        Returns:
            List of indexed document IDs
        """
        if not isinstance(input_data, list):
            raise ValueError("Input must be a list of IndexedDocument objects")

        config = config or {}
        collection_name = config.get("collection_name")

        if not collection_name:
            raise ValueError("collection_name is required in config")

        return await self.index(input_data, collection_name, **config)
