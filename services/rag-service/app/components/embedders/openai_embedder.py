"""OpenAI embeddings using the OpenAI API."""

from typing import Any, Dict, List, Optional

from app.components.embedders.base import BaseEmbedder
from app.components.embedders.factory import EmbedderFactory
from app.config import get_settings


class OpenAIEmbedder(BaseEmbedder):
    """Embedder using OpenAI's embedding models."""

    name: str = "openai"
    description: str = "OpenAI embeddings (text-embedding-3-small, text-embedding-3-large)"

    # Model dimensions
    MODEL_DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    DEFAULT_MODEL = "text-embedding-3-small"

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        """Initialize OpenAI embedder.

        Args:
            model: Model name to use
            api_key: OpenAI API key (uses env var if not provided)
        """
        super().__init__()
        settings = get_settings()
        self.model = model or settings.openai_embedding_model or self.DEFAULT_MODEL
        self.api_key = api_key or settings.openai_api_key
        self.dimension = self.MODEL_DIMENSIONS.get(self.model, 1536)
        self._client = None

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "default": cls.DEFAULT_MODEL,
                    "enum": list(cls.MODEL_DIMENSIONS.keys()),
                    "description": "OpenAI embedding model to use",
                },
                "batch_size": {
                    "type": "integer",
                    "default": 100,
                    "description": "Maximum texts per API call",
                    "minimum": 1,
                    "maximum": 2048,
                },
            },
        }

    @property
    def client(self):
        """Lazy-load OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise ImportError("openai package is required. Install with: pip install openai")

            if not self.api_key:
                raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")

            self._client = AsyncOpenAI(api_key=self.api_key)

        return self._client

    async def embed(
        self,
        texts: List[str],
        model: Optional[str] = None,
        batch_size: int = 100,
        **kwargs,
    ) -> List[List[float]]:
        """Generate embeddings using OpenAI API.

        Args:
            texts: List of texts to embed
            model: Model to use (overrides default)
            batch_size: Maximum texts per API call

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        model = model or self.model
        all_embeddings = []

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            # Clean texts (OpenAI has issues with empty strings)
            batch = [text if text.strip() else " " for text in batch]

            response = await self.client.embeddings.create(
                model=model,
                input=batch,
            )

            # Extract embeddings in order
            batch_embeddings = [None] * len(batch)
            for item in response.data:
                batch_embeddings[item.index] = item.embedding

            all_embeddings.extend(batch_embeddings)

        return all_embeddings


# Register with factory
EmbedderFactory.register("openai", OpenAIEmbedder)
