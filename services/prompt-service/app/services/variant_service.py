"""Variant service - handles prompt variant operations with versioning."""

from typing import Optional
import math

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import PromptVariant, VariantStatus, HistoryAction
from app.models.schemas import (
    CreateVariantRequest,
    UpdateVariantRequest,
    ActivateVariantRequest,
    ChangeVariantStatusRequest,
    PromptVariantResponse,
    VariantListResponse,
    VariantHistoryResponse,
    HistoryListResponse,
)
from app.repositories.generation_repository import GenerationRepository
from app.repositories.variant_repository import VariantRepository
from app.repositories.history_repository import HistoryRepository


class VariantNotFoundError(Exception):
    """Raised when a variant is not found."""

    def __init__(self, variant_id: str):
        self.variant_id = variant_id
        super().__init__(f"Variant '{variant_id}' not found")


class GenerationNotFoundError(Exception):
    """Raised when a generation is not found."""

    def __init__(self, generation_id: str):
        self.generation_id = generation_id
        super().__init__(f"Generation '{generation_id}' not found")


class VariantService:
    """Service for prompt variant management with versioning.

    This service:
    - Creates variants from generations
    - Manages version history (never deletes, only archives)
    - Tracks all changes in audit log
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.variant_repo = VariantRepository(session)
        self.generation_repo = GenerationRepository(session)
        self.history_repo = HistoryRepository(session)

    async def create_variant(
        self,
        request: CreateVariantRequest,
    ) -> PromptVariantResponse:
        """Create a new variant from a generation.

        Args:
            request: The create variant request

        Returns:
            PromptVariantResponse

        Raises:
            GenerationNotFoundError: If generation not found
        """
        # Verify generation exists and belongs to user
        generation = await self.generation_repo.get_by_id_and_user(
            request.generation_id,
            request.user_id,
        )
        if not generation:
            raise GenerationNotFoundError(request.generation_id)

        # Use generation's prompt if not provided
        prompt_content = request.prompt_content or generation.generated_prompt

        # Create variant
        variant = await self.variant_repo.create(
            generation_id=request.generation_id,
            user_id=request.user_id,
            name=request.name,
            prompt_content=prompt_content,
            metadata=request.metadata,
            status=VariantStatus.DRAFT,
        )

        # Log creation in history
        await self.history_repo.log_creation(
            variant_id=variant.id,
            user_id=request.user_id,
            content=prompt_content,
            version=variant.version,
        )

        return PromptVariantResponse.model_validate(variant)

    async def get_variant(
        self,
        variant_id: str,
        user_id: str,
    ) -> PromptVariantResponse:
        """Get a variant by ID.

        Args:
            variant_id: The variant ID
            user_id: The user ID

        Returns:
            PromptVariantResponse

        Raises:
            VariantNotFoundError: If not found
        """
        variant = await self.variant_repo.get_by_id_and_user(variant_id, user_id)
        if not variant:
            raise VariantNotFoundError(variant_id)
        return PromptVariantResponse.model_validate(variant)

    async def update_variant(
        self,
        variant_id: str,
        request: UpdateVariantRequest,
    ) -> PromptVariantResponse:
        """Update a variant (creates new version).

        Args:
            variant_id: The variant ID
            request: The update request

        Returns:
            PromptVariantResponse with updated variant

        Raises:
            VariantNotFoundError: If not found
        """
        variant = await self.variant_repo.get_by_id_and_user(variant_id, request.user_id)
        if not variant:
            raise VariantNotFoundError(variant_id)

        # Store old values for history
        old_content = variant.prompt_content
        old_version = variant.version

        # Determine if content is changing
        content_changing = (
            request.prompt_content is not None
            and request.prompt_content != variant.prompt_content
        )

        # Update variant
        updated = await self.variant_repo.update(
            variant=variant,
            name=request.name,
            prompt_content=request.prompt_content,
            metadata=request.metadata,
            increment_version=content_changing,  # Only increment version if content changes
        )

        # Log update in history
        if content_changing:
            await self.history_repo.log_update(
                variant_id=variant_id,
                user_id=request.user_id,
                old_content=old_content,
                new_content=request.prompt_content,
                old_version=old_version,
                new_version=updated.version,
                change_summary=request.change_summary,
            )

        return PromptVariantResponse.model_validate(updated)

    async def activate_variant(
        self,
        variant_id: str,
        request: ActivateVariantRequest,
    ) -> PromptVariantResponse:
        """Activate or deactivate a variant.

        Args:
            variant_id: The variant ID
            request: The activation request

        Returns:
            PromptVariantResponse

        Raises:
            VariantNotFoundError: If not found
        """
        variant = await self.variant_repo.get_by_id_and_user(variant_id, request.user_id)
        if not variant:
            raise VariantNotFoundError(variant_id)

        # Update active status
        updated = await self.variant_repo.set_active(variant, request.is_active)

        # Log in history
        await self.history_repo.log_activation(
            variant_id=variant_id,
            user_id=request.user_id,
            activated=request.is_active,
        )

        return PromptVariantResponse.model_validate(updated)

    async def change_status(
        self,
        variant_id: str,
        request: ChangeVariantStatusRequest,
    ) -> PromptVariantResponse:
        """Change variant status.

        Args:
            variant_id: The variant ID
            request: The status change request

        Returns:
            PromptVariantResponse

        Raises:
            VariantNotFoundError: If not found
        """
        variant = await self.variant_repo.get_by_id_and_user(variant_id, request.user_id)
        if not variant:
            raise VariantNotFoundError(variant_id)

        # Update status
        updated = await self.variant_repo.set_status(variant, request.status)

        # Log archived status change
        if request.status == VariantStatus.ARCHIVED:
            await self.history_repo.log_archived(
                variant_id=variant_id,
                user_id=request.user_id,
            )

        return PromptVariantResponse.model_validate(updated)

    async def list_variants(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[VariantStatus] = None,
        is_active: Optional[bool] = None,
    ) -> VariantListResponse:
        """List variants for a user.

        Args:
            user_id: The user ID
            page: Page number
            page_size: Items per page
            status: Filter by status
            is_active: Filter by active status

        Returns:
            VariantListResponse with paginated results
        """
        variants, total = await self.variant_repo.list_by_user(
            user_id=user_id,
            page=page,
            page_size=page_size,
            status=status,
            is_active=is_active,
        )

        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return VariantListResponse(
            variants=[PromptVariantResponse.model_validate(v) for v in variants],
            count=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def list_variants_by_generation(
        self,
        generation_id: str,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> VariantListResponse:
        """List variants for a specific generation.

        Args:
            generation_id: The generation ID
            user_id: The user ID
            page: Page number
            page_size: Items per page

        Returns:
            VariantListResponse with paginated results
        """
        variants, total = await self.variant_repo.list_by_generation(
            generation_id=generation_id,
            user_id=user_id,
            page=page,
            page_size=page_size,
        )

        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return VariantListResponse(
            variants=[PromptVariantResponse.model_validate(v) for v in variants],
            count=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_variant_history(
        self,
        variant_id: str,
        user_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> HistoryListResponse:
        """Get history for a variant.

        Args:
            variant_id: The variant ID
            user_id: The user ID
            page: Page number
            page_size: Items per page

        Returns:
            HistoryListResponse

        Raises:
            VariantNotFoundError: If variant not found
        """
        # Verify variant exists and belongs to user
        variant = await self.variant_repo.get_by_id_and_user(variant_id, user_id)
        if not variant:
            raise VariantNotFoundError(variant_id)

        history, total = await self.history_repo.get_by_variant(
            variant_id=variant_id,
            page=page,
            page_size=page_size,
        )

        return HistoryListResponse(
            history=[VariantHistoryResponse.model_validate(h) for h in history],
            count=total,
        )

    async def get_active_variant(
        self,
        generation_id: str,
        user_id: str,
    ) -> Optional[PromptVariantResponse]:
        """Get the active variant for a generation.

        Args:
            generation_id: The generation ID
            user_id: The user ID

        Returns:
            PromptVariantResponse or None
        """
        variant = await self.variant_repo.get_active_variant_for_generation(
            generation_id=generation_id,
            user_id=user_id,
        )
        if variant:
            return PromptVariantResponse.model_validate(variant)
        return None
