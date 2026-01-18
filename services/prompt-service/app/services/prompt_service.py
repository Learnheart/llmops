"""Prompt service - handles prompt generation operations."""

from typing import Optional, List, Tuple
import math

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import PromptGeneration
from app.models.schemas import (
    GeneratePromptRequest,
    PromptGenerationResponse,
    GenerationListResponse,
    ComposePromptRequest,
    ComposePromptResponse,
)
from app.repositories.generation_repository import GenerationRepository
from app.services.template_service import TemplateService
from app.templates.registry import TemplateNotFoundError


class PromptGenerationError(Exception):
    """Raised when prompt generation fails."""
    pass


class GenerationNotFoundError(Exception):
    """Raised when a generation is not found."""

    def __init__(self, generation_id: str):
        self.generation_id = generation_id
        super().__init__(f"Generation '{generation_id}' not found")


class PromptService:
    """Service for prompt generation and management.

    This service:
    - Uses TemplateService to build prompts (from CODE)
    - Stores generated prompts in PostgreSQL (DATABASE)
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = GenerationRepository(session)
        self.template_service = TemplateService()

    async def generate_prompt(
        self,
        request: GeneratePromptRequest,
    ) -> PromptGenerationResponse:
        """Generate a prompt and save it to the database.

        Args:
            request: The generation request

        Returns:
            PromptGenerationResponse with the generated prompt

        Raises:
            TemplateNotFoundError: If template key is invalid
            PromptGenerationError: If generation fails
        """
        # Validate template key
        if not self.template_service.validate_template_key(request.template_key):
            raise TemplateNotFoundError(request.template_key)

        try:
            # Build prompt using template
            generated_prompt = self.template_service.build_prompt(
                request.template_key,
                request.agent_instruction,
            )

            # Save to database
            generation = await self.repository.create(
                user_id=request.user_id,
                template_key=request.template_key,
                agent_instruction=request.agent_instruction,
                generated_prompt=generated_prompt,
                metadata=request.metadata,
            )

            return PromptGenerationResponse.model_validate(generation)

        except TemplateNotFoundError:
            raise
        except Exception as e:
            raise PromptGenerationError(f"Failed to generate prompt: {str(e)}")

    async def compose_prompt(
        self,
        request: ComposePromptRequest,
    ) -> ComposePromptResponse:
        """Compose a prompt, optionally saving it.

        Args:
            request: The compose request

        Returns:
            ComposePromptResponse with the composed prompt
        """
        # Validate template key
        if not self.template_service.validate_template_key(request.template_key):
            raise TemplateNotFoundError(request.template_key)

        # Build prompt
        prompt = self.template_service.build_prompt(
            request.template_key,
            request.agent_instruction,
        )

        # Get template info
        template_info = self.template_service.get_template_info(request.template_key)

        generation_id = None
        saved = False

        # Save if requested
        if request.save:
            generation = await self.repository.create(
                user_id=request.user_id,
                template_key=request.template_key,
                agent_instruction=request.agent_instruction,
                generated_prompt=prompt,
                metadata=request.metadata,
            )
            generation_id = generation.id
            saved = True

        return ComposePromptResponse(
            prompt=prompt,
            template_key=request.template_key,
            template_name=template_info.name if template_info else request.template_key,
            generation_id=generation_id,
            saved=saved,
        )

    async def get_generation(
        self,
        generation_id: str,
        user_id: str,
    ) -> PromptGenerationResponse:
        """Get a generation by ID.

        Args:
            generation_id: The generation ID
            user_id: The user ID

        Returns:
            PromptGenerationResponse

        Raises:
            GenerationNotFoundError: If not found
        """
        generation = await self.repository.get_by_id_and_user(generation_id, user_id)
        if not generation:
            raise GenerationNotFoundError(generation_id)
        return PromptGenerationResponse.model_validate(generation)

    async def list_generations(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        template_key: Optional[str] = None,
    ) -> GenerationListResponse:
        """List generations for a user.

        Args:
            user_id: The user ID
            page: Page number (1-indexed)
            page_size: Number of items per page
            template_key: Optional filter by template key

        Returns:
            GenerationListResponse with paginated results
        """
        generations, total = await self.repository.list_by_user(
            user_id=user_id,
            page=page,
            page_size=page_size,
            template_key=template_key,
        )

        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return GenerationListResponse(
            generations=[
                PromptGenerationResponse.model_validate(g) for g in generations
            ],
            count=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def delete_generation(
        self,
        generation_id: str,
        user_id: str,
    ) -> bool:
        """Delete a generation.

        Args:
            generation_id: The generation ID
            user_id: The user ID

        Returns:
            True if deleted, False if not found

        Raises:
            GenerationNotFoundError: If not found
        """
        deleted = await self.repository.delete_by_user(generation_id, user_id)
        if not deleted:
            raise GenerationNotFoundError(generation_id)
        return True
