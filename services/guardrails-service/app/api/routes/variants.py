"""
Variant endpoints for managing guardrail variants with versioning.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db, VariantStatus
from app.models.schemas import (
    CreateVariantRequest,
    UpdateVariantRequest,
    GuardrailVariantResponse,
    ListVariantsRequest,
    ListVariantsResponse,
    SetVariantStatusRequest,
    SetVariantActiveRequest,
    ListHistoryRequest,
    ListHistoryResponse,
)
from app.services.variant_service import (
    VariantService,
    VariantNotFoundError,
    GenerationNotFoundError,
)

router = APIRouter()


@router.post("", response_model=GuardrailVariantResponse, status_code=201, tags=["variants"])
async def create_variant(
    request: CreateVariantRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new guardrail variant from a generation.

    Variants allow users to customize and save specific versions of guardrails.

    Args:
        request: Variant creation request
        db: Database session dependency

    Returns:
        GuardrailVariantResponse: Created variant with version 1

    Raises:
        HTTPException: 404 if generation not found
        HTTPException: 500 if creation fails
    """
    service = VariantService(db)
    try:
        return await service.create_variant(request)
    except GenerationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Variant creation failed: {str(e)}")


@router.get("", response_model=ListVariantsResponse, tags=["variants"])
async def list_variants(
    user_id: str,
    page: int = 1,
    page_size: int = 20,
    generation_id: str = None,
    status: VariantStatus = None,
    is_active: bool = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List guardrail variants for a user with pagination and filters.

    Args:
        user_id: User ID for filtering
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100)
        generation_id: Optional generation ID filter
        status: Optional status filter (draft, active, archived)
        is_active: Optional active state filter
        db: Database session dependency

    Returns:
        ListVariantsResponse: Paginated list of variants

    Raises:
        HTTPException: 400 if pagination parameters invalid
    """
    if page < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=400,
            detail="Invalid pagination parameters. Page must be >= 1, page_size between 1-100"
        )

    service = VariantService(db)
    try:
        generation_uuid = UUID(generation_id) if generation_id else None

        items, total = await service.list_variants(
            user_id=user_id,
            page=page,
            page_size=page_size,
            generation_id=generation_uuid,
            status=status,
            is_active=is_active,
        )

        total_pages = (total + page_size - 1) // page_size

        return ListVariantsResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list variants: {str(e)}")


@router.get("/{variant_id}", response_model=GuardrailVariantResponse, tags=["variants"])
async def get_variant(
    variant_id: UUID,
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific guardrail variant by ID.

    Args:
        variant_id: Variant UUID
        user_id: User ID for access control
        db: Database session dependency

    Returns:
        GuardrailVariantResponse: Variant details

    Raises:
        HTTPException: 404 if variant not found or access denied
    """
    service = VariantService(db)
    variant = await service.get_variant(variant_id, user_id)

    if not variant:
        raise HTTPException(
            status_code=404,
            detail=f"Variant '{variant_id}' not found or access denied"
        )

    return variant


@router.post("/{variant_id}/versions", response_model=GuardrailVariantResponse, status_code=201, tags=["variants"])
async def create_new_version(
    variant_id: UUID,
    request: UpdateVariantRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new version of a guardrail variant.

    This follows the "insert-only" principle - instead of updating the existing variant,
    a new version is created. The old version remains unchanged for audit purposes.

    Args:
        variant_id: Source variant UUID (will create new version from this)
        request: New version request with updated content
        db: Database session dependency

    Returns:
        GuardrailVariantResponse: Newly created variant with incremented version

    Raises:
        HTTPException: 404 if source variant not found or access denied
        HTTPException: 500 if version creation fails
    """
    service = VariantService(db)
    try:
        return await service.create_new_version(variant_id, request)
    except VariantNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Version creation failed: {str(e)}")


@router.post("/{variant_id}/activate", response_model=GuardrailVariantResponse, tags=["variants"])
async def set_variant_active(
    variant_id: UUID,
    request: SetVariantActiveRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Activate or deactivate a guardrail variant.

    Args:
        variant_id: Variant UUID
        request: Activation request
        db: Database session dependency

    Returns:
        GuardrailVariantResponse: Updated variant

    Raises:
        HTTPException: 404 if variant not found or access denied
        HTTPException: 500 if operation fails
    """
    service = VariantService(db)
    try:
        return await service.set_variant_active(variant_id, request)
    except VariantNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Activation failed: {str(e)}")


@router.post("/{variant_id}/status", response_model=GuardrailVariantResponse, tags=["variants"])
async def set_variant_status(
    variant_id: UUID,
    request: SetVariantStatusRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Change the status of a guardrail variant.

    Status can be: draft, active, or archived.

    Args:
        variant_id: Variant UUID
        request: Status change request
        db: Database session dependency

    Returns:
        GuardrailVariantResponse: Updated variant

    Raises:
        HTTPException: 404 if variant not found or access denied
        HTTPException: 500 if operation fails
    """
    service = VariantService(db)
    try:
        return await service.set_variant_status(variant_id, request)
    except VariantNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status change failed: {str(e)}")


@router.delete("/{variant_id}", status_code=204, tags=["variants"])
async def delete_variant(
    variant_id: UUID,
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a guardrail variant.

    This will also delete all associated history entries.

    Args:
        variant_id: Variant UUID
        user_id: User ID for access control
        db: Database session dependency

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: 404 if variant not found or access denied
    """
    service = VariantService(db)
    deleted = await service.delete_variant(variant_id, user_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Variant '{variant_id}' not found or access denied"
        )

    return None


@router.get("/{variant_id}/history", response_model=ListHistoryResponse, tags=["variants"])
async def get_variant_history(
    variant_id: UUID,
    user_id: str,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the change history for a variant.

    Shows all changes, updates, and status changes with full audit trail.

    Args:
        variant_id: Variant UUID
        user_id: User ID for access control
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100)
        db: Database session dependency

    Returns:
        ListHistoryResponse: Paginated history entries

    Raises:
        HTTPException: 404 if variant not found or access denied
        HTTPException: 400 if pagination parameters invalid
    """
    if page < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=400,
            detail="Invalid pagination parameters. Page must be >= 1, page_size between 1-100"
        )

    service = VariantService(db)
    try:
        items, total = await service.get_variant_history(
            variant_id=variant_id,
            user_id=user_id,
            page=page,
            page_size=page_size,
        )

        total_pages = (total + page_size - 1) // page_size

        return ListHistoryResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    except VariantNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")
