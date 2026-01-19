"""
High-level guardrail endpoints for composition and comparison.
These are convenience endpoints that combine multiple operations.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.schemas import (
    CompareTemplatesRequest,
    CompareTemplatesResponse,
    TemplateComparisonResult,
    BatchGenerateRequest,
    BatchGenerateResponse,
)
from app.services.guardrail_service import GuardrailService
from app.templates.registry import TemplateNotFoundError

router = APIRouter()


@router.post("/compare", response_model=CompareTemplatesResponse, tags=["guardrails"])
async def compare_templates(
    request: CompareTemplatesRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Compare multiple guardrail templates with the same context.

    This endpoint allows users to generate guardrails using multiple
    templates simultaneously to compare their outputs.

    Args:
        request: Comparison request with template keys and context
        db: Database session dependency

    Returns:
        CompareTemplatesResponse: Comparison results for all templates

    Raises:
        HTTPException: 400 if any template not found
        HTTPException: 400 if invalid number of templates (must be 2-5)
    """
    if len(request.template_keys) < 2 or len(request.template_keys) > 5:
        raise HTTPException(
            status_code=400,
            detail="Must compare between 2 and 5 templates"
        )

    service = GuardrailService(db)
    try:
        comparisons = await service.compare_templates(request)

        return CompareTemplatesResponse(
            user_context=request.user_context,
            comparisons=comparisons,
            total=len(comparisons),
        )
    except TemplateNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@router.post("/batch", response_model=BatchGenerateResponse, tags=["guardrails"])
async def batch_generate(
    request: BatchGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate multiple guardrails in a single request.

    Useful for bulk generation operations. Failed generations are
    skipped and reported in the response.

    Args:
        request: Batch generation request (max 10 generations)
        db: Database session dependency

    Returns:
        BatchGenerateResponse: Results with success/failure counts

    Raises:
        HTTPException: 400 if invalid number of requests (must be 1-10)
    """
    if len(request.generations) < 1 or len(request.generations) > 10:
        raise HTTPException(
            status_code=400,
            detail="Must provide between 1 and 10 generation requests"
        )

    service = GuardrailService(db)
    try:
        results, successful, failed = await service.batch_generate(request.generations)

        return BatchGenerateResponse(
            results=results,
            total=len(request.generations),
            successful=successful,
            failed=failed,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch generation failed: {str(e)}")
