"""Repository for prompt variant operations."""

from typing import Optional, List
from uuid import uuid4

from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import PromptVariant, VariantStatus


class VariantRepository:
    """Repository for PromptVariant CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        generation_id: str,
        user_id: str,
        name: str,
        prompt_content: str,
        metadata: Optional[dict] = None,
        status: VariantStatus = VariantStatus.DRAFT,
    ) -> PromptVariant:
        """Create a new prompt variant."""
        variant = PromptVariant(
            id=str(uuid4()),
            generation_id=generation_id,
            user_id=user_id,
            name=name,
            prompt_content=prompt_content,
            version=1,
            is_active=True,
            status=status,
            metadata=metadata,
        )
        self.session.add(variant)
        await self.session.commit()
        await self.session.refresh(variant)
        return variant

    async def get_by_id(self, variant_id: str) -> Optional[PromptVariant]:
        """Get a variant by ID."""
        result = await self.session.execute(
            select(PromptVariant).where(PromptVariant.id == variant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_user(
        self,
        variant_id: str,
        user_id: str,
    ) -> Optional[PromptVariant]:
        """Get a variant by ID and user_id."""
        result = await self.session.execute(
            select(PromptVariant).where(
                PromptVariant.id == variant_id,
                PromptVariant.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[VariantStatus] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[List[PromptVariant], int]:
        """List variants for a user with pagination."""
        # Base query
        query = select(PromptVariant).where(PromptVariant.user_id == user_id)

        # Apply filters
        if status:
            query = query.where(PromptVariant.status == status)
        if is_active is not None:
            query = query.where(PromptVariant.is_active == is_active)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        query = (
            query.order_by(desc(PromptVariant.updated_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.session.execute(query)
        variants = result.scalars().all()

        return list(variants), total

    async def list_by_generation(
        self,
        generation_id: str,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[PromptVariant], int]:
        """List variants for a specific generation."""
        query = select(PromptVariant).where(
            and_(
                PromptVariant.generation_id == generation_id,
                PromptVariant.user_id == user_id,
            )
        )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        query = (
            query.order_by(desc(PromptVariant.version))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.session.execute(query)
        variants = result.scalars().all()

        return list(variants), total

    async def update(
        self,
        variant: PromptVariant,
        name: Optional[str] = None,
        prompt_content: Optional[str] = None,
        metadata: Optional[dict] = None,
        increment_version: bool = True,
    ) -> PromptVariant:
        """Update a variant (creates new version)."""
        if name is not None:
            variant.name = name
        if prompt_content is not None:
            variant.prompt_content = prompt_content
        if metadata is not None:
            variant.metadata = metadata
        if increment_version:
            variant.version += 1

        await self.session.commit()
        await self.session.refresh(variant)
        return variant

    async def set_active(
        self,
        variant: PromptVariant,
        is_active: bool,
    ) -> PromptVariant:
        """Set variant active status."""
        variant.is_active = is_active
        await self.session.commit()
        await self.session.refresh(variant)
        return variant

    async def set_status(
        self,
        variant: PromptVariant,
        status: VariantStatus,
    ) -> PromptVariant:
        """Set variant status."""
        variant.status = status
        await self.session.commit()
        await self.session.refresh(variant)
        return variant

    async def get_active_variant_for_generation(
        self,
        generation_id: str,
        user_id: str,
    ) -> Optional[PromptVariant]:
        """Get the active variant for a generation."""
        result = await self.session.execute(
            select(PromptVariant).where(
                and_(
                    PromptVariant.generation_id == generation_id,
                    PromptVariant.user_id == user_id,
                    PromptVariant.is_active == True,
                    PromptVariant.status == VariantStatus.ACTIVE,
                )
            ).order_by(desc(PromptVariant.version)).limit(1)
        )
        return result.scalar_one_or_none()
