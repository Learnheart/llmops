"""
Variant Service - manages guardrail variant operations.
Handles variant creation, updates, versioning, and history tracking.
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import GuardrailVariant, VariantStatus
from app.models.schemas import (
    CreateVariantRequest,
    UpdateVariantRequest,
    GuardrailVariantResponse,
    SetVariantStatusRequest,
    SetVariantActiveRequest,
    GuardrailVariantHistoryResponse,
)
from app.repositories.variant_repository import VariantRepository
from app.repositories.generation_repository import GenerationRepository
from app.repositories.history_repository import HistoryRepository


class VariantNotFoundError(Exception):
    """Raised when a variant is not found."""

    def __init__(self, variant_id: UUID):
        super().__init__(f"Variant '{variant_id}' not found")


class GenerationNotFoundError(Exception):
    """Raised when a generation is not found."""

    def __init__(self, generation_id: UUID):
        super().__init__(f"Generation '{generation_id}' not found")


class VariantService:
    """
    Service for guardrail variant management.

    Handles variant CRUD operations, versioning, and history tracking.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize service with database session.

        Args:
            db: Async database session
        """
        self.db = db
        self.variant_repo = VariantRepository(db)
        self.generation_repo = GenerationRepository(db)
        self.history_repo = HistoryRepository(db)

    async def create_variant(
        self, request: CreateVariantRequest
    ) -> GuardrailVariantResponse:
        """
        Create a new variant from a generation.

        Args:
            request: Variant creation request

        Returns:
            GuardrailVariantResponse: Created variant

        Raises:
            GenerationNotFoundError: If generation doesn't exist or access denied
        """
        # Verify generation exists and belongs to user
        generation = await self.generation_repo.get_by_id_and_user(
            UUID(request.generation_id), request.user_id
        )
        if not generation:
            raise GenerationNotFoundError(UUID(request.generation_id))

        # Use generation's content if custom content not provided
        guardrail_content = request.guardrail_content or generation.generated_guardrail

        # Create variant
        variant = await self.variant_repo.create(
            generation_id=UUID(request.generation_id),
            user_id=request.user_id,
            name=request.name,
            description=request.description,
            guardrail_content=guardrail_content,
            status=request.status or VariantStatus.DRAFT,
            tags=request.tags,
            metadata=request.metadata,
        )

        # Log creation in history
        await self.history_repo.log_creation(
            variant_id=variant.id,
            user_id=request.user_id,
            content=guardrail_content,
            version=1,
            status=variant.status,
            metadata=request.metadata,
        )

        return self._to_response(variant)

    async def get_variant(
        self, variant_id: UUID, user_id: str
    ) -> Optional[GuardrailVariantResponse]:
        """
        Get a variant by ID (user-scoped).

        Args:
            variant_id: Variant UUID
            user_id: User ID for access control

        Returns:
            Optional[GuardrailVariantResponse]: Variant if found, None otherwise
        """
        variant = await self.variant_repo.get_by_id_and_user(variant_id, user_id)
        if not variant:
            return None
        return self._to_response(variant)

    async def list_variants(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        generation_id: Optional[UUID] = None,
        status: Optional[VariantStatus] = None,
        is_active: Optional[bool] = None,
        tags: Optional[List[str]] = None,
    ) -> tuple[List[GuardrailVariantResponse], int]:
        """
        List variants for a user with pagination and filters.

        Args:
            user_id: User ID
            page: Page number
            page_size: Items per page
            generation_id: Optional generation filter
            status: Optional status filter
            is_active: Optional active state filter
            tags: Optional tags filter

        Returns:
            tuple: (list of variants, total count)
        """
        variants, total = await self.variant_repo.list_by_user(
            user_id=user_id,
            page=page,
            page_size=page_size,
            generation_id=generation_id,
            status=status,
            is_active=is_active,
            tags=tags,
        )
        responses = [self._to_response(var) for var in variants]
        return responses, total

    async def create_new_version(
        self, source_variant_id: UUID, request: UpdateVariantRequest
    ) -> GuardrailVariantResponse:
        """
        Create a new version of a variant (insert-only, no update).

        This follows the versioning principle: never update existing records,
        always create new versions. The source variant remains unchanged.

        Args:
            source_variant_id: Source variant UUID to create new version from
            request: New version request with updated content

        Returns:
            GuardrailVariantResponse: Newly created variant with incremented version

        Raises:
            VariantNotFoundError: If source variant doesn't exist or access denied
        """
        # Get source variant
        source_variant = await self.variant_repo.get_by_id_and_user(source_variant_id, request.user_id)
        if not source_variant:
            raise VariantNotFoundError(source_variant_id)

        # Determine new version number
        new_version = source_variant.version + 1

        # Use provided values or keep from source variant
        new_name = request.name if request.name else source_variant.name
        new_description = request.description if request.description is not None else source_variant.description
        new_content = request.guardrail_content if request.guardrail_content else source_variant.guardrail_content
        new_tags = request.tags if request.tags is not None else source_variant.tags
        new_metadata = request.metadata if request.metadata is not None else source_variant.metadata

        # Create new variant (new record, not update)
        new_variant = await self.variant_repo.create(
            generation_id=source_variant.generation_id,
            user_id=request.user_id,
            name=new_name,
            description=new_description,
            guardrail_content=new_content,
            status=source_variant.status,  # Keep same status
            tags=new_tags,
            metadata=new_metadata,
        )

        # Manually set version (override default version=1)
        new_variant.version = new_version
        await self.db.commit()
        await self.db.refresh(new_variant)

        # Log creation of new version in history
        await self.history_repo.log_update(
            variant_id=new_variant.id,
            user_id=request.user_id,
            old_content=source_variant.guardrail_content,
            new_content=new_content,
            old_version=source_variant.version,
            new_version=new_version,
            change_summary=request.change_summary or f"Created new version from v{source_variant.version}",
            metadata={"source_variant_id": str(source_variant_id)},
        )

        return self._to_response(new_variant)

    async def set_variant_active(
        self, variant_id: UUID, request: SetVariantActiveRequest
    ) -> GuardrailVariantResponse:
        """
        Activate or deactivate a variant.

        Args:
            variant_id: Variant UUID
            request: Activation request

        Returns:
            GuardrailVariantResponse: Updated variant

        Raises:
            VariantNotFoundError: If variant doesn't exist or access denied
        """
        # Get variant
        variant = await self.variant_repo.get_by_id_and_user(variant_id, request.user_id)
        if not variant:
            raise VariantNotFoundError(variant_id)

        # Update active state
        variant = await self.variant_repo.set_active(variant, request.is_active)

        # Log activation/deactivation
        await self.history_repo.log_activation(
            variant_id=variant.id,
            user_id=request.user_id,
            activated=request.is_active,
        )

        return self._to_response(variant)

    async def set_variant_status(
        self, variant_id: UUID, request: SetVariantStatusRequest
    ) -> GuardrailVariantResponse:
        """
        Change variant status.

        Args:
            variant_id: Variant UUID
            request: Status change request

        Returns:
            GuardrailVariantResponse: Updated variant

        Raises:
            VariantNotFoundError: If variant doesn't exist or access denied
        """
        # Get variant
        variant = await self.variant_repo.get_by_id_and_user(variant_id, request.user_id)
        if not variant:
            raise VariantNotFoundError(variant_id)

        # Store old status for history
        old_status = variant.status

        # Update status
        variant = await self.variant_repo.set_status(variant, request.status)

        # Log status change
        await self.history_repo.log_status_change(
            variant_id=variant.id,
            user_id=request.user_id,
            old_status=old_status,
            new_status=request.status,
        )

        return self._to_response(variant)

    async def delete_variant(self, variant_id: UUID, user_id: str) -> bool:
        """
        Delete a variant (user-scoped).

        Args:
            variant_id: Variant UUID
            user_id: User ID for access control

        Returns:
            bool: True if deleted, False if not found
        """
        return await self.variant_repo.delete_by_user(variant_id, user_id)

    async def get_variant_history(
        self, variant_id: UUID, user_id: str, page: int = 1, page_size: int = 20
    ) -> tuple[List[GuardrailVariantHistoryResponse], int]:
        """
        Get history for a variant.

        Args:
            variant_id: Variant UUID
            user_id: User ID for access control
            page: Page number
            page_size: Items per page

        Returns:
            tuple: (list of history entries, total count)

        Raises:
            VariantNotFoundError: If variant doesn't exist or access denied
        """
        # Verify variant exists and belongs to user
        variant = await self.variant_repo.get_by_id_and_user(variant_id, user_id)
        if not variant:
            raise VariantNotFoundError(variant_id)

        # Get history
        history_entries, total = await self.history_repo.get_by_variant(
            variant_id=variant_id,
            page=page,
            page_size=page_size,
        )

        responses = [self._history_to_response(entry) for entry in history_entries]
        return responses, total

    async def list_variants_by_generation(
        self, generation_id: UUID, user_id: str
    ) -> List[GuardrailVariantResponse]:
        """
        List all variants for a specific generation.

        Args:
            generation_id: Generation UUID
            user_id: User ID for access control

        Returns:
            List[GuardrailVariantResponse]: List of variants

        Raises:
            GenerationNotFoundError: If generation doesn't exist or access denied
        """
        # Verify generation exists and belongs to user
        generation = await self.generation_repo.get_by_id_and_user(generation_id, user_id)
        if not generation:
            raise GenerationNotFoundError(generation_id)

        # Get variants
        variants = await self.variant_repo.list_by_generation(generation_id, user_id)
        return [self._to_response(var) for var in variants]

    def _to_response(self, variant: GuardrailVariant) -> GuardrailVariantResponse:
        """
        Convert database model to response schema.

        Args:
            variant: Database model

        Returns:
            GuardrailVariantResponse: Response schema
        """
        return GuardrailVariantResponse(
            id=str(variant.id),
            generation_id=str(variant.generation_id),
            user_id=variant.user_id,
            name=variant.name,
            description=variant.description,
            guardrail_content=variant.guardrail_content,
            version=variant.version,
            is_active=variant.is_active,
            status=variant.status,
            tags=variant.tags,
            metadata=variant.metadata,
            created_at=variant.created_at,
            updated_at=variant.updated_at,
        )

    def _history_to_response(self, history) -> GuardrailVariantHistoryResponse:
        """
        Convert history model to response schema.

        Args:
            history: Database model

        Returns:
            GuardrailVariantHistoryResponse: Response schema
        """
        return GuardrailVariantHistoryResponse(
            id=str(history.id),
            variant_id=str(history.variant_id),
            user_id=history.user_id,
            action=history.action,
            old_content=history.old_content,
            new_content=history.new_content,
            old_version=history.old_version,
            new_version=history.new_version,
            old_status=history.old_status,
            new_status=history.new_status,
            change_summary=history.change_summary,
            metadata=history.metadata,
            created_at=history.created_at,
        )
