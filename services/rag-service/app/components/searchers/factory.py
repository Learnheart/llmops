"""Searcher factory for creating search components."""

from typing import Dict, Type

from app.components.base.factory import BaseFactory
from app.components.base.registry import ComponentRegistry
from app.components.searchers.base import BaseSearcher


class SearcherFactory(BaseFactory):
    """Factory for creating search component instances."""

    category: str = "searchers"
    _registry: Dict[str, Type[BaseSearcher]] = {}


# Register the factory with the central registry
ComponentRegistry.register_factory("searchers", SearcherFactory)
