"""
Repository for GuardrailGeneration CRUD operations.
Handles database access for guardrail generations.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import GuardrailGeneration


class GenerationRepository:
    """Repository for managing guardrail generations in the database."""

    def __init__(self, db: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            db: Async database session
        """
        self.db = db

    async def create(
        self,
        user_id: str,
        template_key: str,
        user_context: str,
        generated_guardrail: str,
        parameters: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> GuardrailGeneration:
        """
        Create a new guardrail generation.

        Args:
            user_id: ID of the user creating the generation
            template_key: Key of the template used
            user_context: User-provided context
            generated_guardrail: Generated guardrail content
            parameters: Template parameters used
            metadata: Additional metadata

        Returns:
            GuardrailGeneration: Created generation instance
        """
        generation = GuardrailGeneration(
            user_id=user_id,
            template_key=template_key,
            user_context=user_context,
            generated_guardrail=generated_guardrail,
            parameters=parameters,
            metadata=metadata,
        )
        self.db.add(generation)
        await self.db.commit()
        await self.db.refresh(generation)
        return generation

    async def get_by_id(self, generation_id: UUID) -> Optional[GuardrailGeneration]:
        """
        Get a generation by ID.

        Args:
            generation_id: Generation UUID

        Returns:
            Optional[GuardrailGeneration]: Generation if found, None otherwise
        """
        result = await self.db.execute(
            select(GuardrailGeneration).where(GuardrailGeneration.id == generation_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_user(
        self, generation_id: UUID, user_id: str
    ) -> Optional[GuardrailGeneration]:
        """
        Get a generation by ID and user (for access control).

        Excludes soft-deleted records.

        Args:
            generation_id: Generation UUID
            user_id: User ID

        Returns:
            Optional[GuardrailGeneration]: Generation if found and belongs to user, None otherwise
        """
        result = await self.db.execute(
            select(GuardrailGeneration).where(
                GuardrailGeneration.id == generation_id,
                GuardrailGeneration.user_id == user_id,
                GuardrailGeneration.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        template_key: Optional[str] = None,
        include_deleted: bool = False,
    ) -> tuple[List[GuardrailGeneration], int]:
        """
        List generations for a user with pagination and filtering.

        Args:
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Number of items per page
            template_key: Optional template key filter
            include_deleted: Whether to include soft-deleted records (default False)

        Returns:
            tuple: (list of generations, total count)
        """
        # Build query
        query = select(GuardrailGeneration).where(GuardrailGeneration.user_id == user_id)

        # Exclude soft-deleted by default
        if not include_deleted:
            query = query.where(GuardrailGeneration.is_deleted == False)

        if template_key:
            query = query.where(GuardrailGeneration.template_key == template_key)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Apply pagination and ordering
        query = (
            query.order_by(GuardrailGeneration.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def delete(self, generation_id: UUID, deleted_by: Optional[str] = None) -> bool:
        """
        Soft delete a generation (mark as deleted, don't physically remove).

        Preserves the record for audit trail while hiding it from normal queries.

        Args:
            generation_id: Generation UUID
            deleted_by: User ID who performed the deletion

        Returns:
            bool: True if deleted, False if not found
        """
        generation = await self.get_by_id(generation_id)
        if not generation:
            return False

        generation.is_deleted = True
        generation.deleted_at = datetime.utcnow()
        generation.deleted_by = deleted_by
        await self.db.commit()
        return True

    async def delete_by_user(self, generation_id: UUID, user_id: str) -> bool:
        """
        Soft delete a generation (user-scoped for access control).

        Preserves the record for audit trail while hiding it from normal queries.

        Args:
            generation_id: Generation UUID
            user_id: User ID (also recorded as deleted_by)

        Returns:
            bool: True if deleted, False if not found or access denied
        """
        generation = await self.get_by_id_and_user(generation_id, user_id)
        if not generation:
            return False

        generation.is_deleted = True
        generation.deleted_at = datetime.utcnow()
        generation.deleted_by = user_id
        await self.db.commit()
        return True

    async def hard_delete(self, generation_id: UUID) -> bool:
        """
        Permanently delete a generation (use with caution - for admin/cleanup only).

        WARNING: This permanently removes the record and cannot be undone.
        Use soft delete (delete_by_user) for normal operations.

        Args:
            generation_id: Generation UUID

        Returns:
            bool: True if deleted, False if not found
        """
        generation = await self.get_by_id(generation_id)
        if not generation:
            return False

        await self.db.delete(generation)
        await self.db.commit()
        return True

    async def restore(self, generation_id: UUID, user_id: str) -> Optional[GuardrailGeneration]:
        """
        Restore a soft-deleted generation.

        Args:
            generation_id: Generation UUID
            user_id: User ID for access control

        Returns:
            Optional[GuardrailGeneration]: Restored generation or None if not found
        """
        result = await self.db.execute(
            select(GuardrailGeneration).where(
                GuardrailGeneration.id == generation_id,
                GuardrailGeneration.user_id == user_id,
                GuardrailGeneration.is_deleted == True,
            )
        )
        generation = result.scalar_one_or_none()
        if not generation:
            return None

        generation.is_deleted = False
        generation.deleted_at = None
        generation.deleted_by = None
        await self.db.commit()
        await self.db.refresh(generation)
        return generation

    async def count_by_user(self, user_id: str, template_key: Optional[str] = None) -> int:
        """
        Count generations for a user.

        Args:
            user_id: User ID
            template_key: Optional template key filter

        Returns:
            int: Number of generations
        """
        query = select(func.count()).where(GuardrailGeneration.user_id == user_id)

        if template_key:
            query = query.where(GuardrailGeneration.template_key == template_key)

        result = await self.db.execute(query)
        return result.scalar_one()

    async def get_recent_by_template(
        self, user_id: str, template_key: str, limit: int = 5
    ) -> List[GuardrailGeneration]:
        """
        Get recent generations for a specific template.

        Args:
            user_id: User ID
            template_key: Template key
            limit: Maximum number of results

        Returns:
            List[GuardrailGeneration]: Recent generations
        """
        query = (
            select(GuardrailGeneration)
            .where(
                GuardrailGeneration.user_id == user_id,
                GuardrailGeneration.template_key == template_key,
            )
            .order_by(GuardrailGeneration.created_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())
