"""Document retrieval endpoints."""

import time
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.database import (
    get_db,
    PipelineRun,
    PipelineType,
    PipelineRunStatus,
)
from app.models.schemas import (
    RetrievalRequest,
    RetrievalResponse,
    BatchRetrievalRequest,
    BatchRetrievalResponse,
    BatchQueryResult,
    ChunkResult,
)
from app.services.retrieval_service import RetrievalService

router = APIRouter()
settings = get_settings()


@router.post("", response_model=RetrievalResponse)
async def retrieve_documents(
    request: RetrievalRequest,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve relevant documents for a query.

    This endpoint:
    1. Embeds the query
    2. Searches using the configured searcher
    3. Applies optimizer chain
    4. Returns top results with scores
    """
    start_time = time.time()

    # Create retrieval service
    service = RetrievalService(db)

    try:
        # Run retrieval pipeline
        result = await service.retrieve(
            user_id=request.user_id,
            knowledge_base_id=request.knowledge_base_id,
            query=request.query,
            config=request.config,
            top_k=request.top_k,
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Retrieval failed: {str(e)}",
        )


@router.post("/batch", response_model=BatchRetrievalResponse)
async def batch_retrieve_documents(
    request: BatchRetrievalRequest,
    db: AsyncSession = Depends(get_db),
):
    """Batch retrieve for multiple queries.

    Processes all queries with the same configuration
    and returns results for each.
    """
    start_time = time.time()

    service = RetrievalService(db)
    all_results = []

    try:
        for query in request.queries:
            result = await service.retrieve(
                user_id=request.user_id,
                knowledge_base_id=request.knowledge_base_id,
                query=query,
                config=request.config,
                top_k=request.top_k,
            )

            all_results.append(
                BatchQueryResult(
                    query=query,
                    results=result.results,
                    total_results=result.total_results,
                )
            )

        duration_ms = (time.time() - start_time) * 1000

        return BatchRetrievalResponse(
            run_id=str(uuid4()),
            queries_processed=len(request.queries),
            results=all_results,
            metrics={
                "duration_ms": round(duration_ms, 2),
                "avg_duration_per_query_ms": round(duration_ms / len(request.queries), 2),
            },
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch retrieval failed: {str(e)}",
        )


@router.post("/search")
async def simple_search(
    query: str,
    knowledge_base_id: str,
    user_id: str,
    top_k: int = 5,
    db: AsyncSession = Depends(get_db),
):
    """Simple search endpoint with minimal configuration.

    Uses default retrieval settings for quick searches.
    """
    from app.models.schemas import RetrievalPipelineConfig

    service = RetrievalService(db)

    try:
        result = await service.retrieve(
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            query=query,
            config=RetrievalPipelineConfig(),
            top_k=top_k,
        )

        return {
            "query": query,
            "results": [r.model_dump() for r in result.results],
            "total": result.total_results,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}",
        )
