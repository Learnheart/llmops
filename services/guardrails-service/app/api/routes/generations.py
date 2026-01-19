"""
Generation endpoints for creating and managing guardrail generations.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.schemas import (
    GenerateGuardrailRequest,
    GuardrailGenerationResponse,
    ListGenerationsRequest,
    ListGenerationsResponse,
)
from app.services.guardrail_service import GuardrailService
from app.templates.registry import TemplateNotFoundError

router = APIRouter()


@router.post("", response_model=GuardrailGenerationResponse, status_code=201, tags=["generations"])
async def generate_guardrail(
    request: GenerateGuardrailRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a new guardrail and save to database.

    Creates a guardrail using the specified template and saves it for
    future reference and variant creation.

    Args:
        request: Generation request with template, context, and parameters
        db: Database session dependency

    Returns:
        GuardrailGenerationResponse: Generated guardrail information

    Raises:
        HTTPException: 400 if template not found
        HTTPException: 500 if generation fails
    """
    service = GuardrailService(db)
    try:
        return await service.generate_guardrail(request)
    except TemplateNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.get("", response_model=ListGenerationsResponse, tags=["generations"])
async def list_generations(
    user_id: str,
    page: int = 1,
    page_size: int = 20,
    template_key: str = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List guardrail generations for a user with pagination.

    Args:
        user_id: User ID for filtering
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100)
        template_key: Optional template key filter
        db: Database session dependency

    Returns:
        ListGenerationsResponse: Paginated list of generations

    Raises:
        HTTPException: 400 if pagination parameters invalid
    """
    if page < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=400,
            detail="Invalid pagination parameters. Page must be >= 1, page_size between 1-100"
        )

    service = GuardrailService(db)
    try:
        items, total = await service.list_generations(
            user_id=user_id,
            page=page,
            page_size=page_size,
            template_key=template_key,
        )

        total_pages = (total + page_size - 1) // page_size

        return ListGenerationsResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list generations: {str(e)}")


@router.get("/{generation_id}", response_model=GuardrailGenerationResponse, tags=["generations"])
async def get_generation(
    generation_id: UUID,
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific guardrail generation by ID.

    Args:
        generation_id: Generation UUID
        user_id: User ID for access control
        db: Database session dependency

    Returns:
        GuardrailGenerationResponse: Generation details

    Raises:
        HTTPException: 404 if generation not found or access denied
    """
    service = GuardrailService(db)
    generation = await service.get_generation(generation_id, user_id)

    if not generation:
        raise HTTPException(
            status_code=404,
            detail=f"Generation '{generation_id}' not found or access denied"
        )

    return generation


@router.delete("/{generation_id}", status_code=204, tags=["generations"])
async def delete_generation(
    generation_id: UUID,
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a guardrail generation.

    This will also delete all associated variants due to cascade delete.

    Args:
        generation_id: Generation UUID
        user_id: User ID for access control
        db: Database session dependency

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: 404 if generation not found or access denied
    """
    service = GuardrailService(db)
    deleted = await service.delete_generation(generation_id, user_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Generation '{generation_id}' not found or access denied"
        )

    return None
