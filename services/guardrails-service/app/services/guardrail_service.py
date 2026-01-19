"""
Guardrail Service - orchestrates guardrail generation and management.
Coordinates between templates, LLM, and database repositories.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import GuardrailGeneration
from app.models.schemas import (
    GenerateGuardrailRequest,
    GuardrailGenerationResponse,
    CompareTemplatesRequest,
    TemplateComparisonResult,
)
from app.repositories.generation_repository import GenerationRepository
from app.services.template_service import TemplateService
from app.services.llm_service import LLMService
from app.templates.registry import TemplateNotFoundError


class GuardrailService:
    """
    Service for guardrail generation and management.

    Orchestrates between template service and database repositories
    to generate and store guardrails.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize service with database session.

        Args:
            db: Async database session
        """
        self.db = db
        self.generation_repo = GenerationRepository(db)
        self.template_service = TemplateService()
        self.llm_service = LLMService()

    async def _auto_select_template(
        self,
        user_context: str,
        instruction: Optional[str] = None
    ) -> str:
        """
        Use LLM to automatically select the best template based on context.

        Args:
            user_context: User-provided context
            instruction: Optional detailed instruction for template selection

        Returns:
            str: Selected template key

        Raises:
            Exception: If LLM call fails
        """
        # Get all available templates
        templates = self.template_service.list_all_templates()

        # Build template descriptions for LLM
        template_descriptions = "\n".join([
            f"- {t['key']}: {t['description']}"
            for t in templates
        ])

        # Build selection prompt
        selection_prompt = f"""You are an expert guardrail template selector. Based on the user's context and requirements, select the MOST APPROPRIATE guardrail template.

Available Templates:
{template_descriptions}

User Context:
{user_context}

{f'Additional Requirements/Instruction:\n{instruction}' if instruction else ''}

Analyze the user's needs carefully and consider:
1. The primary risk or concern in the context
2. The type of data being handled (personal, medical, financial, etc.)
3. The industry or domain
4. Regulatory requirements if mentioned
5. The specific goal the user wants to achieve

Respond with ONLY the template key (e.g., "content_safety", "pii_protection", "factual_accuracy", "tone_control", or "compliance").
Do not include any explanation, just the key."""

        # Call LLM to select template
        try:
            selected_key = await self.llm_service.generate(
                prompt=selection_prompt,
                temperature=0.3,  # Low temperature for consistent selection
                max_tokens=50
            )

            # Clean the response
            selected_key = selected_key.strip().lower().replace('"', '').replace("'", "")

            # Validate the selected key
            if not self.template_service.validate_template_key(selected_key):
                # Fallback to content_safety if LLM returns invalid key
                print(f"Warning: LLM selected invalid key '{selected_key}', falling back to 'content_safety'")
                selected_key = "content_safety"

            return selected_key

        except Exception as e:
            # On any error, fallback to content_safety
            print(f"Error in auto template selection: {e}, falling back to 'content_safety'")
            return "content_safety"

    async def generate_guardrail(
        self, request: GenerateGuardrailRequest
    ) -> GuardrailGenerationResponse:
        """
        Generate a new guardrail and save to database.

        Supports two modes:
        - manual: User provides template_key
        - auto: AI selects best template based on context and instruction

        Args:
            request: Generation request with mode, context, and parameters

        Returns:
            GuardrailGenerationResponse: Generated guardrail information

        Raises:
            TemplateNotFoundError: If template doesn't exist (manual mode)
            ValueError: If mode is invalid or required fields missing
        """
        # Determine template key based on mode
        if request.mode == "auto":
            # Auto mode: Use LLM to select best template
            template_key = await self._auto_select_template(
                user_context=request.user_context,
                instruction=request.instruction
            )
        else:
            # Manual mode: Use user-provided template_key
            template_key = request.template_key
            # Validate template exists
            if not self.template_service.validate_template_key(template_key):
                raise TemplateNotFoundError(template_key)

        # Build guardrail using selected template
        generated_guardrail = self.template_service.build_guardrail(
            template_key=template_key,
            user_context=request.user_context,
            parameters=request.parameters,
        )

        # Prepare metadata with mode information
        metadata = request.metadata or {}
        metadata.update({
            "mode": request.mode,
            "auto_selected": request.mode == "auto",
        })
        if request.mode == "auto":
            metadata["selected_template_key"] = template_key
            if request.instruction:
                metadata["instruction"] = request.instruction

        # Save to database
        generation = await self.generation_repo.create(
            user_id=request.user_id,
            template_key=template_key,  # Save the selected template
            user_context=request.user_context,
            generated_guardrail=generated_guardrail,
            parameters=request.parameters,
            metadata=metadata,
        )

        return self._to_response(generation)

    async def get_generation(
        self, generation_id: UUID, user_id: str
    ) -> Optional[GuardrailGenerationResponse]:
        """
        Get a generation by ID (user-scoped).

        Args:
            generation_id: Generation UUID
            user_id: User ID for access control

        Returns:
            Optional[GuardrailGenerationResponse]: Generation if found, None otherwise
        """
        generation = await self.generation_repo.get_by_id_and_user(generation_id, user_id)
        if not generation:
            return None
        return self._to_response(generation)

    async def list_generations(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        template_key: Optional[str] = None,
    ) -> tuple[List[GuardrailGenerationResponse], int]:
        """
        List generations for a user with pagination.

        Args:
            user_id: User ID
            page: Page number
            page_size: Items per page
            template_key: Optional template filter

        Returns:
            tuple: (list of generations, total count)
        """
        generations, total = await self.generation_repo.list_by_user(
            user_id=user_id,
            page=page,
            page_size=page_size,
            template_key=template_key,
        )
        responses = [self._to_response(gen) for gen in generations]
        return responses, total

    async def delete_generation(self, generation_id: UUID, user_id: str) -> bool:
        """
        Delete a generation (user-scoped).

        Args:
            generation_id: Generation UUID
            user_id: User ID for access control

        Returns:
            bool: True if deleted, False if not found
        """
        return await self.generation_repo.delete_by_user(generation_id, user_id)

    async def compare_templates(
        self, request: CompareTemplatesRequest
    ) -> List[TemplateComparisonResult]:
        """
        Compare multiple templates with the same context.

        Args:
            request: Comparison request with template keys and context

        Returns:
            List[TemplateComparisonResult]: Comparison results

        Raises:
            TemplateNotFoundError: If any template doesn't exist
        """
        results = []

        for template_key in request.template_keys:
            # Validate template exists
            if not self.template_service.validate_template_key(template_key):
                raise TemplateNotFoundError(template_key)

            # Generate guardrail
            generated_guardrail = self.template_service.build_guardrail(
                template_key=template_key,
                user_context=request.user_context,
                parameters=request.parameters,
            )

            # Get template info
            template_info = self.template_service.get_template_info(template_key)

            results.append(
                TemplateComparisonResult(
                    template_key=template_key,
                    template_name=template_info["name"],
                    generated_guardrail=generated_guardrail,
                    parameters=request.parameters,
                )
            )

        return results

    async def batch_generate(
        self, requests: List[GenerateGuardrailRequest]
    ) -> tuple[List[GuardrailGenerationResponse], int, int]:
        """
        Generate multiple guardrails at once.

        Args:
            requests: List of generation requests

        Returns:
            tuple: (successful results, successful count, failed count)
        """
        results = []
        successful = 0
        failed = 0

        for request in requests:
            try:
                result = await self.generate_guardrail(request)
                results.append(result)
                successful += 1
            except Exception:
                # Log error in production
                failed += 1
                continue

        return results, successful, failed

    def _to_response(self, generation: GuardrailGeneration) -> GuardrailGenerationResponse:
        """
        Convert database model to response schema.

        Args:
            generation: Database model

        Returns:
            GuardrailGenerationResponse: Response schema
        """
        return GuardrailGenerationResponse(
            id=str(generation.id),
            user_id=generation.user_id,
            template_key=generation.template_key,
            user_context=generation.user_context,
            generated_guardrail=generation.generated_guardrail,
            parameters=generation.parameters,
            metadata=generation.metadata,
            created_at=generation.created_at,
        )
