"""Base embedder class for text embeddings."""

from abc import abstractmethod
from typing import Any, Dict, List, Optional, Union
import numpy as np

from app.components.base.component import BaseComponent


class BaseEmbedder(BaseComponent):
    """Abstract base class for text embedders.

    Embedders convert text into dense vector representations
    for semantic search and similarity comparisons.
    """

    category: str = "embedders"
    dimension: int = 0  # Output embedding dimension

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Return configuration schema for embedder."""
        return {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Model name/ID to use for embeddings",
                },
                "batch_size": {
                    "type": "integer",
                    "default": 100,
                    "description": "Maximum texts to embed in one batch",
                    "minimum": 1,
                    "maximum": 1000,
                },
            },
        }

    @abstractmethod
    async def embed(
        self,
        texts: List[str],
        **kwargs,
    ) -> List[List[float]]:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed
            **kwargs: Additional embedder-specific options

        Returns:
            List of embedding vectors (as lists of floats)
        """
        pass

    async def embed_single(self, text: str, **kwargs) -> List[float]:
        """Embed a single text string.

        Args:
            text: Text to embed
            **kwargs: Additional options

        Returns:
            Embedding vector as list of floats
        """
        results = await self.embed([text], **kwargs)
        return results[0]

    async def process(
        self,
        input_data: Any,
        config: Optional[Dict[str, Any]] = None,
    ) -> List[List[float]]:
        """Process method implementing BaseComponent interface.

        Args:
            input_data: Text string or list of strings
            config: Embedder configuration options

        Returns:
            List of embedding vectors
        """
        config = config or {}

        if isinstance(input_data, str):
            return await self.embed([input_data], **config)
        elif isinstance(input_data, list):
            return await self.embed(input_data, **config)
        else:
            raise ValueError("Input must be a string or list of strings")

    def get_dimension(self) -> int:
        """Get the embedding dimension.

        Returns:
            Number of dimensions in the embedding vectors
        """
        return self.dimension

    def to_dict(self) -> Dict[str, Any]:
        """Convert component metadata to dictionary."""
        result = super().to_dict()
        result["dimension"] = self.dimension
        return result
