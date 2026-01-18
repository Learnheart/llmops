"""Generation endpoints - CRUD for prompt generations in DATABASE."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.schemas import (
    GeneratePromptRequest,
    PromptGenerationResponse,
    GenerationListResponse,
    VariantListResponse,
)
from app.services.prompt_service import (
    PromptService,
    GenerationNotFoundError,
    PromptGenerationError,
)
from app.services.variant_service import VariantService
from app.templates.registry import TemplateNotFoundError

router = APIRouter(prefix="/generations")


@router.post("", response_model=PromptGenerationResponse, status_code=201)
async def generate_prompt(
    request: GeneratePromptRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate a new prompt and save it to database.

    Uses a template from CODE to generate the prompt,
    then stores the result in the DATABASE.
    """
    service = PromptService(db)
    try:
        return await service.generate_prompt(request)
    except TemplateNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PromptGenerationError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=GenerationListResponse)
async def list_generations(
    user_id: str = Query(..., description="User ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    template_key: Optional[str] = Query(None, description="Filter by template"),
    db: AsyncSession = Depends(get_db),
):
    """List prompt generations for a user."""
    service = PromptService(db)
    return await service.list_generations(
        user_id=user_id,
        page=page,
        page_size=page_size,
        template_key=template_key,
    )


@router.get("/{generation_id}", response_model=PromptGenerationResponse)
async def get_generation(
    generation_id: str,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific generation by ID."""
    service = PromptService(db)
    try:
        return await service.get_generation(generation_id, user_id)
    except GenerationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{generation_id}", status_code=204)
async def delete_generation(
    generation_id: str,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
):
    """Delete a generation.

    Note: This also deletes all associated variants.
    """
    service = PromptService(db)
    try:
        await service.delete_generation(generation_id, user_id)
    except GenerationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{generation_id}/variants", response_model=VariantListResponse)
async def list_generation_variants(
    generation_id: str,
    user_id: str = Query(..., description="User ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """List all variants for a specific generation."""
    variant_service = VariantService(db)
    return await variant_service.list_variants_by_generation(
        generation_id=generation_id,
        user_id=user_id,
        page=page,
        page_size=page_size,
    )
