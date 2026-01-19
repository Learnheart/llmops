"""
Repository for GuardrailVariantHistory operations.
Handles audit logging for all variant changes.
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import GuardrailVariantHistory, HistoryAction, VariantStatus


class HistoryRepository:
    """Repository for managing variant history audit logs."""

    def __init__(self, db: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            db: Async database session
        """
        self.db = db

    async def log_creation(
        self,
        variant_id: UUID,
        user_id: str,
        content: str,
        version: int,
        status: VariantStatus,
        metadata: Optional[dict] = None,
    ) -> GuardrailVariantHistory:
        """
        Log variant creation.

        Args:
            variant_id: Variant UUID
            user_id: User ID
            content: Initial content
            version: Initial version
            status: Initial status
            metadata: Optional metadata

        Returns:
            GuardrailVariantHistory: Created history entry
        """
        history = GuardrailVariantHistory(
            variant_id=variant_id,
            user_id=user_id,
            action=HistoryAction.CREATED,
            new_content=content,
            new_version=version,
            new_status=status,
            change_summary="Variant created",
            metadata=metadata,
        )
        self.db.add(history)
        await self.db.commit()
        await self.db.refresh(history)
        return history

    async def log_update(
        self,
        variant_id: UUID,
        user_id: str,
        old_content: str,
        new_content: str,
        old_version: int,
        new_version: int,
        change_summary: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> GuardrailVariantHistory:
        """
        Log variant update.

        Args:
            variant_id: Variant UUID
            user_id: User ID
            old_content: Previous content
            new_content: New content
            old_version: Previous version
            new_version: New version
            change_summary: Summary of changes
            metadata: Optional metadata

        Returns:
            GuardrailVariantHistory: Created history entry
        """
        history = GuardrailVariantHistory(
            variant_id=variant_id,
            user_id=user_id,
            action=HistoryAction.UPDATED,
            old_content=old_content,
            new_content=new_content,
            old_version=old_version,
            new_version=new_version,
            change_summary=change_summary or "Variant updated",
            metadata=metadata,
        )
        self.db.add(history)
        await self.db.commit()
        await self.db.refresh(history)
        return history

    async def log_activation(
        self,
        variant_id: UUID,
        user_id: str,
        activated: bool,
        metadata: Optional[dict] = None,
    ) -> GuardrailVariantHistory:
        """
        Log variant activation/deactivation.

        Args:
            variant_id: Variant UUID
            user_id: User ID
            activated: Whether variant was activated (True) or deactivated (False)
            metadata: Optional metadata

        Returns:
            GuardrailVariantHistory: Created history entry
        """
        action = HistoryAction.ACTIVATED if activated else HistoryAction.DEACTIVATED
        summary = "Variant activated" if activated else "Variant deactivated"

        history = GuardrailVariantHistory(
            variant_id=variant_id,
            user_id=user_id,
            action=action,
            change_summary=summary,
            metadata=metadata,
        )
        self.db.add(history)
        await self.db.commit()
        await self.db.refresh(history)
        return history

    async def log_status_change(
        self,
        variant_id: UUID,
        user_id: str,
        old_status: VariantStatus,
        new_status: VariantStatus,
        metadata: Optional[dict] = None,
    ) -> GuardrailVariantHistory:
        """
        Log variant status change.

        Args:
            variant_id: Variant UUID
            user_id: User ID
            old_status: Previous status
            new_status: New status
            metadata: Optional metadata

        Returns:
            GuardrailVariantHistory: Created history entry
        """
        action = HistoryAction.ARCHIVED if new_status == VariantStatus.ARCHIVED else HistoryAction.STATUS_CHANGED
        summary = f"Status changed from {old_status.value} to {new_status.value}"

        history = GuardrailVariantHistory(
            variant_id=variant_id,
            user_id=user_id,
            action=action,
            old_status=old_status,
            new_status=new_status,
            change_summary=summary,
            metadata=metadata,
        )
        self.db.add(history)
        await self.db.commit()
        await self.db.refresh(history)
        return history

    async def get_by_variant(
        self,
        variant_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[GuardrailVariantHistory], int]:
        """
        Get history entries for a variant with pagination.

        Args:
            variant_id: Variant UUID
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            tuple: (list of history entries, total count)
        """
        # Build query
        query = select(GuardrailVariantHistory).where(
            GuardrailVariantHistory.variant_id == variant_id
        )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Apply pagination and ordering
        query = (
            query.order_by(GuardrailVariantHistory.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def get_latest_by_variant(
        self, variant_id: UUID, limit: int = 10
    ) -> List[GuardrailVariantHistory]:
        """
        Get latest history entries for a variant.

        Args:
            variant_id: Variant UUID
            limit: Maximum number of entries to return

        Returns:
            List[GuardrailVariantHistory]: Latest history entries
        """
        result = await self.db.execute(
            select(GuardrailVariantHistory)
            .where(GuardrailVariantHistory.variant_id == variant_id)
            .order_by(GuardrailVariantHistory.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[GuardrailVariantHistory], int]:
        """
        Get all history entries for a user with pagination.

        Args:
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            tuple: (list of history entries, total count)
        """
        # Build query
        query = select(GuardrailVariantHistory).where(
            GuardrailVariantHistory.user_id == user_id
        )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Apply pagination and ordering
        query = (
            query.order_by(GuardrailVariantHistory.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def count_by_variant(self, variant_id: UUID) -> int:
        """
        Count history entries for a variant.

        Args:
            variant_id: Variant UUID

        Returns:
            int: Number of history entries
        """
        result = await self.db.execute(
            select(func.count()).where(GuardrailVariantHistory.variant_id == variant_id)
        )
        return result.scalar_one()

    async def get_by_id(self, history_id: UUID) -> Optional[GuardrailVariantHistory]:
        """
        Get a history entry by ID.

        Args:
            history_id: History entry UUID

        Returns:
            Optional[GuardrailVariantHistory]: History entry if found, None otherwise
        """
        result = await self.db.execute(
            select(GuardrailVariantHistory).where(GuardrailVariantHistory.id == history_id)
        )
        return result.scalar_one_or_none()
