"""Chunker factory for creating text chunkers."""

from typing import Dict, Type

from app.components.base.factory import BaseFactory
from app.components.base.registry import ComponentRegistry
from app.components.chunkers.base import BaseChunker


class ChunkerFactory(BaseFactory):
    """Factory for creating text chunker instances."""

    category: str = "chunkers"
    _registry: Dict[str, Type[BaseChunker]] = {}


# Register the factory with the central registry
ComponentRegistry.register_factory("chunkers", ChunkerFactory)
