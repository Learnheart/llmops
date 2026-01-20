"""Document ingestion endpoints."""

import time
from datetime import datetime
from typing import List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.database import (
    get_db,
    Document,
    Chunk,
    KnowledgeBase,
    PipelineRun,
    PipelineType,
    PipelineRunStatus,
    DocumentStatus,
)
from app.models.schemas import (
    IngestionRequest,
    IngestionResponse,
    DocumentResult,
    BatchIngestionRequest,
)
from app.services.ingestion_service import IngestionService

router = APIRouter()
settings = get_settings()


@router.post("", response_model=IngestionResponse, status_code=201)
async def ingest_documents(
    request: IngestionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Ingest documents into a knowledge base.

    This endpoint:
    1. Creates a pipeline run record
    2. For each document:
       - Downloads from storage (MinIO)
       - Parses the document
       - Chunks the content
       - Generates embeddings
       - Indexes in vector store
    3. Returns results with metrics
    """
    start_time = time.time()

    # Create ingestion service
    service = IngestionService(db)

    try:
        # Run ingestion pipeline
        result = await service.ingest(
            user_id=request.user_id,
            knowledge_base_id=request.knowledge_base_id,
            documents=request.documents,
            config=request.config,
        )

        return result

    except Exception as e:
        # Log error and return error response
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {str(e)}",
        )


@router.post("/batch", response_model=IngestionResponse)
async def batch_ingest_documents(
    request: BatchIngestionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Batch ingest multiple documents.

    If async_mode is True, returns immediately with a run_id
    that can be used to check progress.
    """
    if request.async_mode:
        # Create pipeline run record for async tracking
        run = PipelineRun(
            id=str(uuid4()),
            user_id=request.user_id,
            knowledge_base_id=request.knowledge_base_id,
            pipeline_type=PipelineType.INGESTION,
            config=request.config.model_dump(),
            status=PipelineRunStatus.PENDING,
        )
        db.add(run)
        await db.commit()

        # TODO: Queue async job via NATS

        return IngestionResponse(
            run_id=run.id,
            status="pending",
            documents_processed=0,
            total_chunks_created=0,
            results=[],
            metrics={"async": True},
        )

    # Synchronous batch processing
    service = IngestionService(db)

    try:
        result = await service.ingest(
            user_id=request.user_id,
            knowledge_base_id=request.knowledge_base_id,
            documents=request.documents,
            config=request.config,
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch ingestion failed: {str(e)}",
        )


@router.get("/status/{run_id}")
async def get_ingestion_status(
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get status of an ingestion run."""
    from sqlalchemy import select

    result = await db.execute(
        select(PipelineRun).where(PipelineRun.id == run_id)
    )
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return {
        "run_id": run.id,
        "status": run.status.value,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "result": run.result,
        "error": run.error_message,
        "metrics": run.metrics,
    }
