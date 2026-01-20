"""Elasticsearch indexer for full-text search."""

from typing import Any, Dict, List, Optional

from app.components.indexers.base import BaseIndexer, IndexedDocument
from app.components.indexers.factory import IndexerFactory
from app.config import get_settings


class ElasticsearchIndexer(BaseIndexer):
    """Indexer using Elasticsearch for full-text search.

    Elasticsearch provides powerful text search capabilities
    with BM25 ranking.
    """

    name: str = "elasticsearch"
    description: str = "Elasticsearch for full-text search with BM25 ranking"

    def __init__(self, url: Optional[str] = None):
        """Initialize Elasticsearch indexer.

        Args:
            url: Elasticsearch URL
        """
        super().__init__()
        settings = get_settings()
        self.url = url or settings.elasticsearch_url
        self.index_prefix = settings.elasticsearch_index_prefix
        self._client = None

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "collection_name": {
                    "type": "string",
                    "description": "Name of the Elasticsearch index",
                },
                "analyzer": {
                    "type": "string",
                    "default": "standard",
                    "description": "Text analyzer to use",
                },
                "number_of_shards": {
                    "type": "integer",
                    "default": 1,
                    "description": "Number of shards",
                },
                "number_of_replicas": {
                    "type": "integer",
                    "default": 0,
                    "description": "Number of replicas",
                },
            },
            "required": ["collection_name"],
        }

    @property
    def client(self):
        """Lazy-load Elasticsearch client."""
        if self._client is None:
            try:
                from elasticsearch import AsyncElasticsearch
            except ImportError:
                raise ImportError(
                    "elasticsearch is required. Install with: pip install elasticsearch"
                )

            self._client = AsyncElasticsearch(hosts=[self.url])

        return self._client

    def _get_full_index_name(self, name: str) -> str:
        """Get full index name with prefix."""
        if name.startswith(self.index_prefix):
            return name
        return f"{self.index_prefix}{name}"

    async def create_collection(
        self,
        collection_name: str,
        dimension: int = 0,
        analyzer: str = "standard",
        number_of_shards: int = 1,
        number_of_replicas: int = 0,
        **kwargs,
    ) -> bool:
        """Create an Elasticsearch index.

        Args:
            collection_name: Index name
            dimension: Vector dimension (not used for full-text)
            analyzer: Text analyzer
            number_of_shards: Number of shards
            number_of_replicas: Number of replicas

        Returns:
            True if created successfully
        """
        full_name = self._get_full_index_name(collection_name)

        # Check if exists
        if await self.client.indices.exists(index=full_name):
            return True

        # Define index settings and mappings
        settings = {
            "number_of_shards": number_of_shards,
            "number_of_replicas": number_of_replicas,
            "analysis": {
                "analyzer": {
                    "custom_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase", "stop", "snowball"],
                    }
                }
            },
        }

        mappings = {
            "properties": {
                "id": {"type": "keyword"},
                "content": {
                    "type": "text",
                    "analyzer": analyzer,
                    "fields": {
                        "keyword": {"type": "keyword", "ignore_above": 256}
                    },
                },
                "metadata": {
                    "type": "object",
                    "enabled": True,
                },
                "timestamp": {"type": "date"},
            }
        }

        # Create index
        await self.client.indices.create(
            index=full_name,
            settings=settings,
            mappings=mappings,
        )

        return True

    async def index(
        self,
        documents: List[IndexedDocument],
        collection_name: str,
        **kwargs,
    ) -> List[str]:
        """Index documents into Elasticsearch.

        Args:
            documents: Documents to index
            collection_name: Target index

        Returns:
            List of indexed IDs
        """
        full_name = self._get_full_index_name(collection_name)
        ids = []

        # Bulk index
        operations = []
        for doc in documents:
            operations.append({"index": {"_index": full_name, "_id": doc.id}})
            operations.append({
                "id": doc.id,
                "content": doc.content,
                "metadata": doc.metadata or {},
            })
            ids.append(doc.id)

        if operations:
            await self.client.bulk(operations=operations, refresh=True)

        return ids

    async def delete(
        self,
        ids: List[str],
        collection_name: str,
        **kwargs,
    ) -> int:
        """Delete documents from Elasticsearch.

        Args:
            ids: Document IDs to delete
            collection_name: Index name

        Returns:
            Number of deleted documents
        """
        full_name = self._get_full_index_name(collection_name)

        # Bulk delete
        operations = []
        for doc_id in ids:
            operations.append({"delete": {"_index": full_name, "_id": doc_id}})

        if operations:
            result = await self.client.bulk(operations=operations, refresh=True)
            return len(ids)

        return 0

    async def collection_exists(self, collection_name: str) -> bool:
        """Check if index exists.

        Args:
            collection_name: Index name

        Returns:
            True if exists
        """
        full_name = self._get_full_index_name(collection_name)
        return await self.client.indices.exists(index=full_name)

    async def close(self):
        """Close the Elasticsearch client."""
        if self._client:
            await self._client.close()


# Register with factory
IndexerFactory.register("elasticsearch", ElasticsearchIndexer)
