"""Variant endpoints - CRUD for prompt variants with versioning."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db, VariantStatus
from app.models.schemas import (
    CreateVariantRequest,
    UpdateVariantRequest,
    ActivateVariantRequest,
    ChangeVariantStatusRequest,
    PromptVariantResponse,
    VariantListResponse,
    HistoryListResponse,
)
from app.services.variant_service import (
    VariantService,
    VariantNotFoundError,
    GenerationNotFoundError,
)

router = APIRouter(prefix="/variants")


@router.post("", response_model=PromptVariantResponse, status_code=201)
async def create_variant(
    request: CreateVariantRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new variant from a generation.

    Variants allow users to customize and version their prompts.
    """
    service = VariantService(db)
    try:
        return await service.create_variant(request)
    except GenerationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("", response_model=VariantListResponse)
async def list_variants(
    user_id: str = Query(..., description="User ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[VariantStatus] = Query(None, description="Filter by status"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
):
    """List variants for a user."""
    service = VariantService(db)
    return await service.list_variants(
        user_id=user_id,
        page=page,
        page_size=page_size,
        status=status,
        is_active=is_active,
    )


@router.get("/{variant_id}", response_model=PromptVariantResponse)
async def get_variant(
    variant_id: str,
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific variant by ID."""
    service = VariantService(db)
    try:
        return await service.get_variant(variant_id, user_id)
    except VariantNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{variant_id}", response_model=PromptVariantResponse)
async def update_variant(
    variant_id: str,
    request: UpdateVariantRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a variant (creates new version if content changes).

    Version is automatically incremented when prompt_content changes.
    Changes are logged in the audit history.
    """
    service = VariantService(db)
    try:
        return await service.update_variant(variant_id, request)
    except VariantNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{variant_id}/activate", response_model=PromptVariantResponse)
async def activate_variant(
    variant_id: str,
    request: ActivateVariantRequest,
    db: AsyncSession = Depends(get_db),
):
    """Activate or deactivate a variant."""
    service = VariantService(db)
    try:
        return await service.activate_variant(variant_id, request)
    except VariantNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{variant_id}/status", response_model=PromptVariantResponse)
async def change_variant_status(
    variant_id: str,
    request: ChangeVariantStatusRequest,
    db: AsyncSession = Depends(get_db),
):
    """Change variant status (draft, active, archived).

    Use this to move variants through their lifecycle.
    Archived variants are never deleted, preserving history.
    """
    service = VariantService(db)
    try:
        return await service.change_status(variant_id, request)
    except VariantNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{variant_id}/history", response_model=HistoryListResponse)
async def get_variant_history(
    variant_id: str,
    user_id: str = Query(..., description="User ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """Get audit history for a variant.

    Shows all changes made to the variant over time.
    """
    service = VariantService(db)
    try:
        return await service.get_variant_history(
            variant_id=variant_id,
            user_id=user_id,
            page=page,
            page_size=page_size,
        )
    except VariantNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
