"""Full-text searcher using Elasticsearch."""

from typing import Any, Dict, List, Optional

from app.components.searchers.base import BaseSearcher, SearchResult
from app.components.searchers.factory import SearcherFactory
from app.config import get_settings


class FulltextSearcher(BaseSearcher):
    """Searcher using Elasticsearch full-text search.

    Uses BM25 algorithm for keyword-based search.
    """

    name: str = "fulltext"
    description: str = "Full-text search using Elasticsearch BM25"

    def __init__(self, url: Optional[str] = None):
        """Initialize full-text searcher.

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
                    "description": "Elasticsearch index to search",
                },
                "top_k": {
                    "type": "integer",
                    "default": 10,
                    "description": "Number of results to return",
                },
                "fuzziness": {
                    "type": "string",
                    "enum": ["AUTO", "0", "1", "2"],
                    "default": "AUTO",
                    "description": "Fuzziness for typo tolerance",
                },
                "operator": {
                    "type": "string",
                    "enum": ["AND", "OR"],
                    "default": "OR",
                    "description": "Query term operator",
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

    async def search(
        self,
        query: str,
        collection_name: str,
        top_k: int = 10,
        fuzziness: str = "AUTO",
        operator: str = "OR",
        **kwargs,
    ) -> List[SearchResult]:
        """Perform full-text search.

        Args:
            query: Search query text
            collection_name: Index to search
            top_k: Number of results
            fuzziness: Fuzziness level
            operator: Query term operator

        Returns:
            List of SearchResult objects
        """
        full_name = self._get_full_index_name(collection_name)

        # Build query
        es_query = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["content", "content.keyword^2"],
                    "type": "best_fields",
                    "fuzziness": fuzziness,
                    "operator": operator.lower(),
                }
            },
            "size": top_k,
            "_source": ["id", "content", "metadata"],
        }

        # Execute search
        response = await self.client.search(
            index=full_name,
            body=es_query,
        )

        # Convert results
        search_results = []
        max_score = response["hits"]["max_score"] or 1.0

        for hit in response["hits"]["hits"]:
            # Normalize score to 0-1
            normalized_score = hit["_score"] / max_score if max_score > 0 else 0

            search_results.append(
                SearchResult(
                    id=hit["_source"].get("id", hit["_id"]),
                    content=hit["_source"].get("content", ""),
                    score=normalized_score,
                    metadata=hit["_source"].get("metadata", {}),
                )
            )

        return search_results

    async def close(self):
        """Close the Elasticsearch client."""
        if self._client:
            await self._client.close()


# Register with factory
SearcherFactory.register("fulltext", FulltextSearcher)
