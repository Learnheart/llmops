"""Base component abstract class for all RAG pipeline components."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseComponent(ABC):
    """Abstract base class for all RAG pipeline components.

    All components (parsers, chunkers, embedders, indexers, searchers, optimizers)
    inherit from this class and implement the required methods.
    """

    # Component metadata - must be defined by subclasses
    name: str = ""
    description: str = ""
    category: str = ""  # parser, chunker, embedder, indexer, searcher, optimizer

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Return JSON schema for component configuration.

        Subclasses should override this to provide their config schema.

        Returns:
            Dictionary with JSON schema for configuration options.
        """
        return {}

    @abstractmethod
    async def process(self, input_data: Any, config: Optional[Dict[str, Any]] = None) -> Any:
        """Process input data and return output.

        This is the main processing method that must be implemented by all components.

        Args:
            input_data: Input data to process (type depends on component category)
            config: Optional configuration overrides

        Returns:
            Processed output (type depends on component category)
        """
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert component metadata to dictionary.

        Returns:
            Dictionary with component information.
        """
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "config_schema": self.get_config_schema(),
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', category='{self.category}')>"
