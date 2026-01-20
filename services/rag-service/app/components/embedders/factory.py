"""Embedder factory for creating text embedders."""

from typing import Dict, Type

from app.components.base.factory import BaseFactory
from app.components.base.registry import ComponentRegistry
from app.components.embedders.base import BaseEmbedder


class EmbedderFactory(BaseFactory):
    """Factory for creating text embedder instances."""

    category: str = "embedders"
    _registry: Dict[str, Type[BaseEmbedder]] = {}


# Register the factory with the central registry
ComponentRegistry.register_factory("embedders", EmbedderFactory)
