"""Semantic searcher using vector similarity."""

from typing import Any, Dict, List, Optional

from app.components.searchers.base import BaseSearcher, SearchResult
from app.components.searchers.factory import SearcherFactory
from app.config import get_settings


class SemanticSearcher(BaseSearcher):
    """Searcher using vector similarity search in Milvus.

    Performs semantic search by comparing query embeddings
    against stored document embeddings.
    """

    name: str = "semantic"
    description: str = "Vector similarity search using embeddings (Milvus)"

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ):
        """Initialize semantic searcher.

        Args:
            host: Milvus host
            port: Milvus port
        """
        super().__init__()
        settings = get_settings()
        self.host = host or settings.milvus_host
        self.port = port or settings.milvus_port
        self.collection_prefix = settings.milvus_collection_prefix
        self._connected = False
        self._embedder = None

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "collection_name": {
                    "type": "string",
                    "description": "Milvus collection to search",
                },
                "top_k": {
                    "type": "integer",
                    "default": 10,
                    "description": "Number of results to return",
                },
                "metric_type": {
                    "type": "string",
                    "enum": ["COSINE", "L2", "IP"],
                    "default": "COSINE",
                    "description": "Distance metric",
                },
                "nprobe": {
                    "type": "integer",
                    "default": 10,
                    "description": "Number of clusters to search (for IVF indexes)",
                },
            },
            "required": ["collection_name"],
        }

    def _ensure_connection(self):
        """Ensure connection to Milvus."""
        if not self._connected:
            try:
                from pymilvus import connections
            except ImportError:
                raise ImportError("pymilvus is required. Install with: pip install pymilvus")

            connections.connect(
                alias="default",
                host=self.host,
                port=self.port,
            )
            self._connected = True

    def _get_full_collection_name(self, name: str) -> str:
        """Get full collection name with prefix."""
        if name.startswith(self.collection_prefix):
            return name
        return f"{self.collection_prefix}{name}"

    async def search(
        self,
        query: str,
        collection_name: str,
        top_k: int = 10,
        query_vector: Optional[List[float]] = None,
        embedder=None,
        metric_type: str = "COSINE",
        nprobe: int = 10,
        **kwargs,
    ) -> List[SearchResult]:
        """Perform semantic search.

        Args:
            query: Search query text
            collection_name: Collection to search
            top_k: Number of results
            query_vector: Pre-computed query embedding (optional)
            embedder: Embedder to use for query (optional)
            metric_type: Distance metric
            nprobe: Clusters to search

        Returns:
            List of SearchResult objects
        """
        from pymilvus import Collection

        self._ensure_connection()
        full_name = self._get_full_collection_name(collection_name)

        # Get query vector
        if query_vector is None:
            if embedder is None:
                raise ValueError("Either query_vector or embedder must be provided")
            vectors = await embedder.embed([query])
            query_vector = vectors[0]

        # Load collection
        collection = Collection(full_name)
        collection.load()

        # Search parameters
        search_params = {
            "metric_type": metric_type,
            "params": {"nprobe": nprobe},
        }

        # Perform search
        results = collection.search(
            data=[query_vector],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            output_fields=["id", "content", "metadata"],
        )

        # Convert results
        search_results = []
        for hits in results:
            for hit in hits:
                # Normalize score to 0-1 range
                if metric_type == "COSINE":
                    # Cosine similarity is already 0-1
                    score = 1 - hit.distance if hit.distance <= 1 else 0
                elif metric_type == "L2":
                    # L2 distance - smaller is better, convert to similarity
                    score = 1 / (1 + hit.distance)
                else:  # IP
                    score = hit.distance

                search_results.append(
                    SearchResult(
                        id=hit.entity.get("id"),
                        content=hit.entity.get("content", ""),
                        score=score,
                        metadata=hit.entity.get("metadata", {}),
                    )
                )

        return search_results


# Register with factory
SearcherFactory.register("semantic", SemanticSearcher)
