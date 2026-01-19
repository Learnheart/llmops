"""
Repository for GuardrailVariant CRUD operations.
Handles database access for guardrail variants with versioning.
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import GuardrailVariant, VariantStatus


class VariantRepository:
    """Repository for managing guardrail variants in the database."""

    def __init__(self, db: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            db: Async database session
        """
        self.db = db

    async def create(
        self,
        generation_id: UUID,
        user_id: str,
        name: str,
        guardrail_content: str,
        description: Optional[str] = None,
        status: VariantStatus = VariantStatus.DRAFT,
        tags: Optional[List[str]] = None,
        metadata: Optional[dict] = None,
    ) -> GuardrailVariant:
        """
        Create a new guardrail variant.

        Args:
            generation_id: ID of the parent generation
            user_id: ID of the user creating the variant
            name: Variant name
            guardrail_content: Guardrail content
            description: Optional description
            status: Initial status
            tags: Optional tags
            metadata: Additional metadata

        Returns:
            GuardrailVariant: Created variant instance
        """
        variant = GuardrailVariant(
            generation_id=generation_id,
            user_id=user_id,
            name=name,
            description=description,
            guardrail_content=guardrail_content,
            version=1,
            is_active=True,
            status=status,
            tags=tags,
            metadata=metadata,
        )
        self.db.add(variant)
        await self.db.commit()
        await self.db.refresh(variant)
        return variant

    async def get_by_id(self, variant_id: UUID) -> Optional[GuardrailVariant]:
        """
        Get a variant by ID.

        Args:
            variant_id: Variant UUID

        Returns:
            Optional[GuardrailVariant]: Variant if found, None otherwise
        """
        result = await self.db.execute(
            select(GuardrailVariant).where(GuardrailVariant.id == variant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_user(
        self, variant_id: UUID, user_id: str
    ) -> Optional[GuardrailVariant]:
        """
        Get a variant by ID and user (for access control).

        Args:
            variant_id: Variant UUID
            user_id: User ID

        Returns:
            Optional[GuardrailVariant]: Variant if found and belongs to user, None otherwise
        """
        result = await self.db.execute(
            select(GuardrailVariant).where(
                GuardrailVariant.id == variant_id,
                GuardrailVariant.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        generation_id: Optional[UUID] = None,
        status: Optional[VariantStatus] = None,
        is_active: Optional[bool] = None,
        tags: Optional[List[str]] = None,
    ) -> tuple[List[GuardrailVariant], int]:
        """
        List variants for a user with pagination and filtering.

        Args:
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Number of items per page
            generation_id: Optional generation ID filter
            status: Optional status filter
            is_active: Optional active state filter
            tags: Optional tags filter (matches any tag)

        Returns:
            tuple: (list of variants, total count)
        """
        # Build query
        query = select(GuardrailVariant).where(GuardrailVariant.user_id == user_id)

        if generation_id:
            query = query.where(GuardrailVariant.generation_id == generation_id)

        if status:
            query = query.where(GuardrailVariant.status == status)

        if is_active is not None:
            query = query.where(GuardrailVariant.is_active == is_active)

        if tags:
            # Match any of the provided tags (JSON array overlap)
            tag_conditions = [
                GuardrailVariant.tags.contains([tag]) for tag in tags
            ]
            query = query.where(or_(*tag_conditions))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Apply pagination and ordering
        query = (
            query.order_by(GuardrailVariant.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update(
        self,
        variant: GuardrailVariant,
        name: Optional[str] = None,
        description: Optional[str] = None,
        guardrail_content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[dict] = None,
        increment_version: bool = True,
    ) -> GuardrailVariant:
        """
        Update a variant.

        Args:
            variant: Variant to update
            name: New name
            description: New description
            guardrail_content: New content
            tags: New tags
            metadata: New metadata
            increment_version: Whether to increment version number

        Returns:
            GuardrailVariant: Updated variant
        """
        if name is not None:
            variant.name = name

        if description is not None:
            variant.description = description

        if guardrail_content is not None:
            variant.guardrail_content = guardrail_content

        if tags is not None:
            variant.tags = tags

        if metadata is not None:
            variant.metadata = metadata

        if increment_version:
            variant.version += 1

        await self.db.commit()
        await self.db.refresh(variant)
        return variant

    async def set_active(
        self, variant: GuardrailVariant, is_active: bool
    ) -> GuardrailVariant:
        """
        Set the active state of a variant.

        Args:
            variant: Variant to update
            is_active: New active state

        Returns:
            GuardrailVariant: Updated variant
        """
        variant.is_active = is_active
        await self.db.commit()
        await self.db.refresh(variant)
        return variant

    async def set_status(
        self, variant: GuardrailVariant, status: VariantStatus
    ) -> GuardrailVariant:
        """
        Set the status of a variant.

        Args:
            variant: Variant to update
            status: New status

        Returns:
            GuardrailVariant: Updated variant
        """
        variant.status = status
        await self.db.commit()
        await self.db.refresh(variant)
        return variant

    async def delete(self, variant_id: UUID) -> bool:
        """
        Delete a variant.

        Args:
            variant_id: Variant UUID

        Returns:
            bool: True if deleted, False if not found
        """
        variant = await self.get_by_id(variant_id)
        if not variant:
            return False

        await self.db.delete(variant)
        await self.db.commit()
        return True

    async def delete_by_user(self, variant_id: UUID, user_id: str) -> bool:
        """
        Delete a variant (user-scoped for access control).

        Args:
            variant_id: Variant UUID
            user_id: User ID

        Returns:
            bool: True if deleted, False if not found or access denied
        """
        variant = await self.get_by_id_and_user(variant_id, user_id)
        if not variant:
            return False

        await self.db.delete(variant)
        await self.db.commit()
        return True

    async def get_active_variant_for_generation(
        self, generation_id: UUID, user_id: str
    ) -> Optional[GuardrailVariant]:
        """
        Get the active variant for a generation.

        Args:
            generation_id: Generation UUID
            user_id: User ID

        Returns:
            Optional[GuardrailVariant]: Active variant if found, None otherwise
        """
        result = await self.db.execute(
            select(GuardrailVariant)
            .where(
                GuardrailVariant.generation_id == generation_id,
                GuardrailVariant.user_id == user_id,
                GuardrailVariant.is_active == True,
                GuardrailVariant.status == VariantStatus.ACTIVE,
            )
            .order_by(GuardrailVariant.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def count_by_generation(self, generation_id: UUID) -> int:
        """
        Count variants for a generation.

        Args:
            generation_id: Generation UUID

        Returns:
            int: Number of variants
        """
        result = await self.db.execute(
            select(func.count()).where(GuardrailVariant.generation_id == generation_id)
        )
        return result.scalar_one()

    async def list_by_generation(
        self, generation_id: UUID, user_id: str
    ) -> List[GuardrailVariant]:
        """
        List all variants for a generation.

        Args:
            generation_id: Generation UUID
            user_id: User ID

        Returns:
            List[GuardrailVariant]: List of variants
        """
        result = await self.db.execute(
            select(GuardrailVariant)
            .where(
                GuardrailVariant.generation_id == generation_id,
                GuardrailVariant.user_id == user_id,
            )
            .order_by(GuardrailVariant.version.desc())
        )
        return list(result.scalars().all())
