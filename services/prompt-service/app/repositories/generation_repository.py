"""Repository for prompt generation operations."""

from typing import Optional, List
from uuid import uuid4

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import PromptGeneration


class GenerationRepository:
    """Repository for PromptGeneration CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: str,
        template_key: str,
        agent_instruction: str,
        generated_prompt: str,
        metadata: Optional[dict] = None,
    ) -> PromptGeneration:
        """Create a new prompt generation."""
        generation = PromptGeneration(
            id=str(uuid4()),
            user_id=user_id,
            template_key=template_key,
            agent_instruction=agent_instruction,
            generated_prompt=generated_prompt,
            metadata=metadata,
        )
        self.session.add(generation)
        await self.session.commit()
        await self.session.refresh(generation)
        return generation

    async def get_by_id(self, generation_id: str) -> Optional[PromptGeneration]:
        """Get a generation by ID."""
        result = await self.session.execute(
            select(PromptGeneration).where(PromptGeneration.id == generation_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_user(
        self,
        generation_id: str,
        user_id: str,
    ) -> Optional[PromptGeneration]:
        """Get a generation by ID and user_id."""
        result = await self.session.execute(
            select(PromptGeneration).where(
                PromptGeneration.id == generation_id,
                PromptGeneration.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        template_key: Optional[str] = None,
    ) -> tuple[List[PromptGeneration], int]:
        """List generations for a user with pagination."""
        # Base query
        query = select(PromptGeneration).where(PromptGeneration.user_id == user_id)

        # Filter by template_key if provided
        if template_key:
            query = query.where(PromptGeneration.template_key == template_key)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        query = (
            query.order_by(desc(PromptGeneration.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.session.execute(query)
        generations = result.scalars().all()

        return list(generations), total

    async def delete(self, generation_id: str) -> bool:
        """Delete a generation by ID."""
        generation = await self.get_by_id(generation_id)
        if generation:
            await self.session.delete(generation)
            await self.session.commit()
            return True
        return False

    async def delete_by_user(self, generation_id: str, user_id: str) -> bool:
        """Delete a generation by ID and user_id."""
        generation = await self.get_by_id_and_user(generation_id, user_id)
        if generation:
            await self.session.delete(generation)
            await self.session.commit()
            return True
        return False
