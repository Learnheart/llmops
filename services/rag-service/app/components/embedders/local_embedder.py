"""Local embeddings using sentence-transformers."""

from typing import Any, Dict, List, Optional

from app.components.embedders.base import BaseEmbedder
from app.components.embedders.factory import EmbedderFactory
from app.config import get_settings


class LocalEmbedder(BaseEmbedder):
    """Embedder using local sentence-transformers models.

    Runs entirely locally without requiring API calls.
    Good for privacy-sensitive applications or offline use.
    """

    name: str = "local"
    description: str = "Local embeddings using sentence-transformers (all-MiniLM-L6-v2, all-mpnet-base-v2)"

    # Model dimensions
    MODEL_DIMENSIONS = {
        "all-MiniLM-L6-v2": 384,
        "all-MiniLM-L12-v2": 384,
        "all-mpnet-base-v2": 768,
        "paraphrase-MiniLM-L6-v2": 384,
        "multi-qa-MiniLM-L6-cos-v1": 384,
        "multi-qa-mpnet-base-dot-v1": 768,
    }

    DEFAULT_MODEL = "all-MiniLM-L6-v2"

    def __init__(self, model: Optional[str] = None):
        """Initialize local embedder.

        Args:
            model: Model name to use
        """
        super().__init__()
        settings = get_settings()
        self.model = model or settings.local_embedding_model or self.DEFAULT_MODEL
        self.dimension = self.MODEL_DIMENSIONS.get(self.model, 384)
        self._encoder = None

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "default": cls.DEFAULT_MODEL,
                    "description": "sentence-transformers model name",
                },
                "batch_size": {
                    "type": "integer",
                    "default": 32,
                    "description": "Batch size for encoding",
                    "minimum": 1,
                    "maximum": 256,
                },
                "normalize": {
                    "type": "boolean",
                    "default": True,
                    "description": "Normalize embeddings to unit length",
                },
                "device": {
                    "type": "string",
                    "enum": ["cpu", "cuda", "auto"],
                    "default": "auto",
                    "description": "Device to run model on",
                },
            },
        }

    @property
    def encoder(self):
        """Lazy-load sentence transformer model."""
        if self._encoder is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required for local embeddings. "
                    "Install with: pip install sentence-transformers"
                )

            self._encoder = SentenceTransformer(self.model)
            # Update dimension from loaded model
            self.dimension = self._encoder.get_sentence_embedding_dimension()

        return self._encoder

    async def embed(
        self,
        texts: List[str],
        model: Optional[str] = None,
        batch_size: int = 32,
        normalize: bool = True,
        device: str = "auto",
        **kwargs,
    ) -> List[List[float]]:
        """Generate embeddings using local model.

        Args:
            texts: List of texts to embed
            model: Model to use (triggers reload if different)
            batch_size: Batch size for encoding
            normalize: Whether to normalize embeddings
            device: Device to use (cpu/cuda/auto)

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Reload model if different
        if model and model != self.model:
            self.model = model
            self._encoder = None

        encoder = self.encoder

        # Set device if specified
        if device != "auto":
            encoder.to(device)

        # Encode texts
        embeddings = encoder.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=normalize,
            show_progress_bar=False,
            convert_to_numpy=True,
        )

        # Convert to list of lists
        return embeddings.tolist()


# Register with factory
EmbedderFactory.register("local", LocalEmbedder)
