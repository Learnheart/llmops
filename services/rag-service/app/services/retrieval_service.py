"""Retrieval service for search pipeline execution."""

import time
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.models.database import (
    Document,
    Chunk,
    PipelineRun,
    PipelineType,
    PipelineRunStatus,
)
from app.models.schemas import (
    RetrievalResponse,
    ChunkResult,
    RetrievalPipelineConfig,
)
from app.components.embedders.factory import EmbedderFactory
from app.components.searchers.factory import SearcherFactory
from app.components.optimizers.factory import OptimizerFactory
from app.components.searchers.base import SearchResult

settings = get_settings()


class RetrievalService:
    """Service for retrieval pipeline execution."""

    def __init__(self, db: AsyncSession):
        """Initialize retrieval service.

        Args:
            db: Database session
        """
        self.db = db

    async def retrieve(
        self,
        user_id: str,
        knowledge_base_id: str,
        query: str,
        config: RetrievalPipelineConfig,
        top_k: int = 5,
    ) -> RetrievalResponse:
        """Execute retrieval pipeline.

        Args:
            user_id: User ID
            knowledge_base_id: Knowledge base ID
            query: Search query
            config: Pipeline configuration
            top_k: Number of results to return

        Returns:
            RetrievalResponse with results
        """
        start_time = time.time()

        # Create pipeline run record
        run = PipelineRun(
            id=str(uuid4()),
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            pipeline_type=PipelineType.RETRIEVAL,
            config=config.model_dump(),
            status=PipelineRunStatus.RUNNING,
            started_at=datetime.utcnow(),
        )
        self.db.add(run)
        await self.db.commit()

        try:
            # Initialize components
            embedder = EmbedderFactory.create(config.embedder.type)
            searcher = SearcherFactory.create(config.searcher.type)

            # Generate query embedding
            embed_start = time.time()
            query_vector = await embedder.embed_single(query)
            embed_time = (time.time() - embed_start) * 1000

            # Determine collection name
            collection_name = f"kb_{user_id}_{knowledge_base_id}"

            # Calculate fetch size (fetch more for optimization)
            fetch_k = top_k
            if config.optimizers:
                fetch_k = top_k * 3  # Fetch more if optimizers will filter

            # Execute search
            search_start = time.time()
            results = await searcher.search(
                query=query,
                collection_name=collection_name,
                top_k=fetch_k,
                query_vector=query_vector,
                embedder=embedder,
                semantic_weight=config.searcher.semantic_weight,
            )
            search_time = (time.time() - search_start) * 1000

            # Apply optimizer chain
            optimize_start = time.time()
            if config.optimizers:
                for opt_config in config.optimizers:
                    optimizer = OptimizerFactory.create(opt_config.type)
                    opt_params = opt_config.model_dump(exclude={"type"}, exclude_none=True)
                    results = await optimizer.optimize(
                        results=results,
                        query=query,
                        **opt_params,
                    )
            optimize_time = (time.time() - optimize_start) * 1000

            # Limit to top_k
            results = results[:top_k]

            # Enrich results with document metadata
            chunk_results = await self._enrich_results(results)

            # Calculate total duration
            duration_ms = (time.time() - start_time) * 1000

            # Update pipeline run
            run.status = PipelineRunStatus.COMPLETED
            run.completed_at = datetime.utcnow()
            run.result = {
                "query": query,
                "results_count": len(chunk_results),
            }
            run.metrics = {
                "duration_ms": round(duration_ms, 2),
                "embed_time_ms": round(embed_time, 2),
                "search_time_ms": round(search_time, 2),
                "optimize_time_ms": round(optimize_time, 2),
                "results_count": len(chunk_results),
            }
            await self.db.commit()

            return RetrievalResponse(
                run_id=run.id,
                query=query,
                results=chunk_results,
                total_results=len(chunk_results),
                metrics=run.metrics,
            )

        except Exception as e:
            run.status = PipelineRunStatus.FAILED
            run.error_message = str(e)
            run.completed_at = datetime.utcnow()
            await self.db.commit()
            raise

    async def _enrich_results(
        self,
        results: List[SearchResult],
    ) -> List[ChunkResult]:
        """Enrich search results with document metadata.

        Args:
            results: Search results

        Returns:
            Enriched ChunkResult objects
        """
        if not results:
            return []

        # Get chunk IDs
        chunk_ids = [r.id for r in results]

        # Query chunks from database
        query = select(Chunk).where(Chunk.id.in_(chunk_ids))
        db_result = await self.db.execute(query)
        chunks_map = {c.id: c for c in db_result.scalars().all()}

        # Get document IDs
        doc_ids = list(set(
            c.document_id for c in chunks_map.values()
        ))

        # Query documents
        doc_query = select(Document).where(Document.id.in_(doc_ids))
        doc_result = await self.db.execute(doc_query)
        docs_map = {d.id: d for d in doc_result.scalars().all()}

        # Build enriched results
        enriched = []
        for result in results:
            chunk = chunks_map.get(result.id)
            doc = docs_map.get(chunk.document_id) if chunk else None

            enriched.append(
                ChunkResult(
                    id=result.id,
                    content=result.content,
                    score=result.score,
                    document_id=chunk.document_id if chunk else "",
                    document_filename=doc.filename if doc else None,
                    chunk_index=chunk.chunk_index if chunk else 0,
                    metadata={
                        **(result.metadata or {}),
                        **(chunk.metadata or {} if chunk else {}),
                    },
                )
            )

        return enriched
