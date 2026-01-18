"""Repository for prompt variant history operations."""

from typing import Optional, List
from uuid import uuid4

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import PromptVariantHistory, HistoryAction


class HistoryRepository:
    """Repository for PromptVariantHistory operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        variant_id: str,
        user_id: str,
        action: HistoryAction,
        old_content: Optional[str] = None,
        new_content: Optional[str] = None,
        old_version: Optional[int] = None,
        new_version: Optional[int] = None,
        change_summary: Optional[str] = None,
    ) -> PromptVariantHistory:
        """Create a new history record."""
        history = PromptVariantHistory(
            id=str(uuid4()),
            variant_id=variant_id,
            user_id=user_id,
            action=action,
            old_content=old_content,
            new_content=new_content,
            old_version=old_version,
            new_version=new_version,
            change_summary=change_summary,
        )
        self.session.add(history)
        await self.session.commit()
        await self.session.refresh(history)
        return history

    async def get_by_variant(
        self,
        variant_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[List[PromptVariantHistory], int]:
        """Get history records for a variant."""
        query = select(PromptVariantHistory).where(
            PromptVariantHistory.variant_id == variant_id
        )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        query = (
            query.order_by(desc(PromptVariantHistory.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.session.execute(query)
        history = result.scalars().all()

        return list(history), total

    async def get_by_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 50,
        action: Optional[HistoryAction] = None,
    ) -> tuple[List[PromptVariantHistory], int]:
        """Get history records for a user."""
        query = select(PromptVariantHistory).where(
            PromptVariantHistory.user_id == user_id
        )

        if action:
            query = query.where(PromptVariantHistory.action == action)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        query = (
            query.order_by(desc(PromptVariantHistory.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.session.execute(query)
        history = result.scalars().all()

        return list(history), total

    async def log_creation(
        self,
        variant_id: str,
        user_id: str,
        content: str,
        version: int,
    ) -> PromptVariantHistory:
        """Log variant creation."""
        return await self.create(
            variant_id=variant_id,
            user_id=user_id,
            action=HistoryAction.CREATED,
            new_content=content,
            new_version=version,
            change_summary="Variant created",
        )

    async def log_update(
        self,
        variant_id: str,
        user_id: str,
        old_content: str,
        new_content: str,
        old_version: int,
        new_version: int,
        change_summary: Optional[str] = None,
    ) -> PromptVariantHistory:
        """Log variant update."""
        return await self.create(
            variant_id=variant_id,
            user_id=user_id,
            action=HistoryAction.UPDATED,
            old_content=old_content,
            new_content=new_content,
            old_version=old_version,
            new_version=new_version,
            change_summary=change_summary or "Variant updated",
        )

    async def log_activation(
        self,
        variant_id: str,
        user_id: str,
        activated: bool,
    ) -> PromptVariantHistory:
        """Log variant activation/deactivation."""
        action = HistoryAction.ACTIVATED if activated else HistoryAction.DEACTIVATED
        summary = "Variant activated" if activated else "Variant deactivated"
        return await self.create(
            variant_id=variant_id,
            user_id=user_id,
            action=action,
            change_summary=summary,
        )

    async def log_archived(
        self,
        variant_id: str,
        user_id: str,
    ) -> PromptVariantHistory:
        """Log variant archived."""
        return await self.create(
            variant_id=variant_id,
            user_id=user_id,
            action=HistoryAction.ARCHIVED,
            change_summary="Variant archived",
        )
