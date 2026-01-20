"""Pipeline configuration and validation endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.database import get_db, PipelineRun, PipelineType, PipelineRunStatus
from app.models.schemas import (
    PipelineValidateRequest,
    PipelineValidateResponse,
    ValidationError,
    IngestionPipelineConfig,
    RetrievalPipelineConfig,
    PipelineRunResponse,
    PipelineRunListResponse,
)
from app.components.base.registry import ComponentRegistry

router = APIRouter()
settings = get_settings()


@router.post("/validate", response_model=PipelineValidateResponse)
async def validate_pipeline_config(request: PipelineValidateRequest):
    """Validate a pipeline configuration.

    Checks that all specified components exist and configurations are valid.
    """
    errors = []
    warnings = []

    config = request.config

    if request.pipeline_type == "ingestion":
        # Validate ingestion pipeline
        errors.extend(_validate_ingestion_config(config))

        # Check for warnings
        chunker_config = config.get("chunker", {})
        if chunker_config.get("type") == "semantic":
            warnings.append("Semantic chunker requires embeddings and may be slower")

        embedder_config = config.get("embedder", {})
        if embedder_config.get("type") == "openai":
            warnings.append("OpenAI embedder requires API key and incurs costs")

    elif request.pipeline_type == "retrieval":
        # Validate retrieval pipeline
        errors.extend(_validate_retrieval_config(config))

        # Check for warnings
        optimizers = config.get("optimizers", [])
        has_reranking = any(o.get("type") == "reranking" for o in optimizers)
        if has_reranking:
            warnings.append("Reranking optimizer adds latency (50-200ms)")

    else:
        errors.append(ValidationError(
            field="pipeline_type",
            message=f"Invalid pipeline type: {request.pipeline_type}",
        ))

    return PipelineValidateResponse(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def _validate_ingestion_config(config: dict) -> List[ValidationError]:
    """Validate ingestion pipeline config."""
    errors = []

    # Check parser
    parser_config = config.get("parser", {})
    parser_type = parser_config.get("type", "auto")
    if not ComponentRegistry.has_component("parsers", parser_type):
        errors.append(ValidationError(
            field="parser.type",
            message=f"Unknown parser type: {parser_type}",
        ))

    # Check chunker
    chunker_config = config.get("chunker", {})
    chunker_type = chunker_config.get("type", "recursive")
    if not ComponentRegistry.has_component("chunkers", chunker_type):
        errors.append(ValidationError(
            field="chunker.type",
            message=f"Unknown chunker type: {chunker_type}",
        ))

    # Check embedder
    embedder_config = config.get("embedder", {})
    embedder_type = embedder_config.get("type", "openai")
    if not ComponentRegistry.has_component("embedders", embedder_type):
        errors.append(ValidationError(
            field="embedder.type",
            message=f"Unknown embedder type: {embedder_type}",
        ))

    # Check indexer
    indexer_config = config.get("indexer", {})
    indexer_type = indexer_config.get("type", "milvus")
    if not ComponentRegistry.has_component("indexers", indexer_type):
        errors.append(ValidationError(
            field="indexer.type",
            message=f"Unknown indexer type: {indexer_type}",
        ))

    return errors


def _validate_retrieval_config(config: dict) -> List[ValidationError]:
    """Validate retrieval pipeline config."""
    errors = []

    # Check searcher
    searcher_config = config.get("searcher", {})
    searcher_type = searcher_config.get("type", "hybrid")
    if not ComponentRegistry.has_component("searchers", searcher_type):
        errors.append(ValidationError(
            field="searcher.type",
            message=f"Unknown searcher type: {searcher_type}",
        ))

    # Check optimizers
    optimizers = config.get("optimizers", [])
    for i, opt in enumerate(optimizers):
        opt_type = opt.get("type")
        if opt_type and not ComponentRegistry.has_component("optimizers", opt_type):
            errors.append(ValidationError(
                field=f"optimizers[{i}].type",
                message=f"Unknown optimizer type: {opt_type}",
            ))

    return errors


@router.get("/templates/ingestion")
async def get_ingestion_template():
    """Get default ingestion pipeline configuration template."""
    return IngestionPipelineConfig().model_dump()


@router.get("/templates/retrieval")
async def get_retrieval_template():
    """Get default retrieval pipeline configuration template."""
    return RetrievalPipelineConfig().model_dump()


@router.get("/runs", response_model=PipelineRunListResponse)
async def list_pipeline_runs(
    user_id: str = Query(..., min_length=1),
    pipeline_type: Optional[str] = Query(None, pattern="^(ingestion|retrieval)$"),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List pipeline runs for a user."""
    from sqlalchemy import select, func

    # Build query
    query = select(PipelineRun).where(PipelineRun.user_id == user_id)

    if pipeline_type:
        query = query.where(PipelineRun.pipeline_type == PipelineType(pipeline_type))

    if status:
        query = query.where(PipelineRun.status == PipelineRunStatus(status))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    query = query.order_by(PipelineRun.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    runs = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return PipelineRunListResponse(
        runs=[PipelineRunResponse.model_validate(r) for r in runs],
        count=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
