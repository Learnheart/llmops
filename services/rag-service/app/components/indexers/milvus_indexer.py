"""Milvus vector database indexer."""

from typing import Any, Dict, List, Optional

from app.components.indexers.base import BaseIndexer, IndexedDocument
from app.components.indexers.factory import IndexerFactory
from app.config import get_settings


class MilvusIndexer(BaseIndexer):
    """Indexer using Milvus vector database.

    Milvus is optimized for vector similarity search at scale.
    """

    name: str = "milvus"
    description: str = "Milvus vector database for high-performance similarity search"

    # Index type options
    INDEX_TYPES = ["IVF_FLAT", "IVF_SQ8", "IVF_PQ", "HNSW", "FLAT"]
    METRIC_TYPES = ["L2", "IP", "COSINE"]

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ):
        """Initialize Milvus indexer.

        Args:
            host: Milvus server host
            port: Milvus server port
        """
        super().__init__()
        settings = get_settings()
        self.host = host or settings.milvus_host
        self.port = port or settings.milvus_port
        self.collection_prefix = settings.milvus_collection_prefix
        self._connected = False

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "collection_name": {
                    "type": "string",
                    "description": "Name of the Milvus collection",
                },
                "dimension": {
                    "type": "integer",
                    "description": "Vector dimension",
                },
                "index_type": {
                    "type": "string",
                    "enum": cls.INDEX_TYPES,
                    "default": "IVF_FLAT",
                    "description": "Index type for vector search",
                },
                "metric_type": {
                    "type": "string",
                    "enum": cls.METRIC_TYPES,
                    "default": "COSINE",
                    "description": "Distance metric",
                },
                "nlist": {
                    "type": "integer",
                    "default": 1024,
                    "description": "Number of cluster units (for IVF indexes)",
                },
            },
            "required": ["collection_name", "dimension"],
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

    async def create_collection(
        self,
        collection_name: str,
        dimension: int,
        index_type: str = "IVF_FLAT",
        metric_type: str = "COSINE",
        nlist: int = 1024,
        **kwargs,
    ) -> bool:
        """Create a Milvus collection.

        Args:
            collection_name: Collection name
            dimension: Vector dimension
            index_type: Index type
            metric_type: Distance metric
            nlist: Number of clusters

        Returns:
            True if created successfully
        """
        from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, utility

        self._ensure_connection()
        full_name = self._get_full_collection_name(collection_name)

        # Check if exists
        if utility.has_collection(full_name):
            return True

        # Define schema
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dimension),
            FieldSchema(name="metadata", dtype=DataType.JSON),
        ]

        schema = CollectionSchema(fields=fields, description=f"RAG collection: {collection_name}")

        # Create collection
        collection = Collection(name=full_name, schema=schema)

        # Create index
        index_params = {
            "index_type": index_type,
            "metric_type": metric_type,
            "params": {"nlist": nlist} if "IVF" in index_type else {},
        }

        collection.create_index(field_name="vector", index_params=index_params)
        collection.load()

        return True

    async def index(
        self,
        documents: List[IndexedDocument],
        collection_name: str,
        **kwargs,
    ) -> List[str]:
        """Index documents into Milvus.

        Args:
            documents: Documents to index
            collection_name: Target collection

        Returns:
            List of indexed IDs
        """
        from pymilvus import Collection

        self._ensure_connection()
        full_name = self._get_full_collection_name(collection_name)

        collection = Collection(full_name)

        # Prepare data
        ids = []
        contents = []
        vectors = []
        metadatas = []

        for doc in documents:
            ids.append(doc.id)
            contents.append(doc.content[:65530])  # Truncate to max length
            vectors.append(doc.vector)
            metadatas.append(doc.metadata or {})

        # Insert data
        data = [ids, contents, vectors, metadatas]
        collection.insert(data)
        collection.flush()

        return ids

    async def delete(
        self,
        ids: List[str],
        collection_name: str,
        **kwargs,
    ) -> int:
        """Delete documents from Milvus.

        Args:
            ids: Document IDs to delete
            collection_name: Collection name

        Returns:
            Number of deleted documents
        """
        from pymilvus import Collection

        self._ensure_connection()
        full_name = self._get_full_collection_name(collection_name)

        collection = Collection(full_name)

        # Delete by expression
        expr = f'id in {ids}'
        result = collection.delete(expr)

        return len(ids)

    async def collection_exists(self, collection_name: str) -> bool:
        """Check if collection exists.

        Args:
            collection_name: Collection name

        Returns:
            True if exists
        """
        from pymilvus import utility

        self._ensure_connection()
        full_name = self._get_full_collection_name(collection_name)

        return utility.has_collection(full_name)


# Register with factory
IndexerFactory.register("milvus", MilvusIndexer)
