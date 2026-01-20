"""Parser factory for creating document parsers."""

from typing import Dict, Type

from app.components.base.factory import BaseFactory
from app.components.base.registry import ComponentRegistry
from app.components.parsers.base import BaseParser


class ParserFactory(BaseFactory):
    """Factory for creating document parser instances."""

    category: str = "parsers"
    _registry: Dict[str, Type[BaseParser]] = {}

    @classmethod
    def get_parser_for_extension(cls, extension: str) -> BaseParser:
        """Get the appropriate parser for a file extension.

        Args:
            extension: File extension (with or without dot)

        Returns:
            Parser instance that supports the extension

        Raises:
            ValueError: If no parser supports the extension
        """
        ext = extension.lower().lstrip(".")

        for name, parser_class in cls._registry.items():
            if name == "auto":
                continue
            instance = parser_class()
            if instance.supports_extension(ext):
                return instance

        raise ValueError(f"No parser found for extension '{ext}'")


# Register the factory with the central registry
ComponentRegistry.register_factory("parsers", ParserFactory)
