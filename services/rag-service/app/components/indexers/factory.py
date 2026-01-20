"""Indexer factory for creating vector indexers."""

from typing import Dict, Type

from app.components.base.factory import BaseFactory
from app.components.base.registry import ComponentRegistry
from app.components.indexers.base import BaseIndexer


class IndexerFactory(BaseFactory):
    """Factory for creating vector indexer instances."""

    category: str = "indexers"
    _registry: Dict[str, Type[BaseIndexer]] = {}


# Register the factory with the central registry
ComponentRegistry.register_factory("indexers", IndexerFactory)
