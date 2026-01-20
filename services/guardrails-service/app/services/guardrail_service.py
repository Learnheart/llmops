"""
Guardrail Service - orchestrates guardrail generation and management.
Coordinates between templates, LLM, and database repositories.
"""

import re
import logging
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import GuardrailGeneration
from app.models.schemas import (
    GenerateGuardrailRequest,
    GuardrailGenerationResponse,
    CompareTemplatesRequest,
    TemplateComparisonResult,
    BatchItemResult,
)
from app.repositories.generation_repository import GenerationRepository
from app.services.template_service import TemplateService
from app.services.llm_service import LLMService
from app.templates.registry import TemplateNotFoundError

logger = logging.getLogger(__name__)


@dataclass
class TemplateSelectionResult:
    """Result of auto template selection."""
    template_key: str
    was_fallback: bool
    fallback_reason: Optional[str] = None


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

    def _parse_template_key(self, response: str, valid_keys: List[str]) -> Optional[str]:
        """
        Extract template key from LLM response with fuzzy matching.

        Handles various response formats:
        - Clean key: "content_safety"
        - With quotes: "content_safety" or 'content_safety'
        - Markdown bold: **content_safety**
        - With explanation: "I recommend content_safety because..."
        - Numbered: "1. content_safety"
        - Dashes: "content-safety" -> "content_safety"

        Args:
            response: Raw LLM response
            valid_keys: List of valid template keys

        Returns:
            Optional[str]: Matched template key or None
        """
        # Clean response
        cleaned = response.strip().lower()
        cleaned = re.sub(r'["\'\*\.\,\:\d\[\]\(\)]', '', cleaned)  # Remove punctuation
        cleaned = cleaned.replace('-', '_')  # Normalize dashes to underscores

        # Direct match
        if cleaned in valid_keys:
            return cleaned

        # Check if any valid key is contained in the cleaned response
        for key in valid_keys:
            if key in cleaned:
                return key

        # Try matching with dashes replaced
        for key in valid_keys:
            if key.replace('_', '-') in response.lower():
                return key

        return None

    async def _auto_select_template(
        self,
        user_context: str,
        instruction: Optional[str] = None
    ) -> TemplateSelectionResult:
        """
        Use LLM to automatically select the best template based on context.

        Returns a TemplateSelectionResult that includes:
        - template_key: The selected (or fallback) template key
        - was_fallback: Whether fallback was used
        - fallback_reason: Explanation if fallback was used

        Args:
            user_context: User-provided context
            instruction: Optional detailed instruction for template selection

        Returns:
            TemplateSelectionResult: Selection result with fallback info
        """
        # Get all available templates
        templates = self.template_service.list_all_templates()
        valid_keys = [t['key'] for t in templates]

        # Build template descriptions for LLM
        template_descriptions = "\n".join([
            f"- {t['key']}: {t['description']}"
            for t in templates
        ])

        # Build selection prompt with strict format requirement
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

IMPORTANT: Respond with EXACTLY one of these keys, nothing else:
{', '.join(valid_keys)}

Your response must be a single word from the list above."""

        # Call LLM to select template
        try:
            raw_response = await self.llm_service.generate(
                prompt=selection_prompt,
                temperature=0.1,  # Lower temperature for more deterministic results
                max_tokens=20  # Shorter to prevent explanation
            )

            # Parse the response with robust matching
            selected_key = self._parse_template_key(raw_response, valid_keys)

            if selected_key:
                return TemplateSelectionResult(
                    template_key=selected_key,
                    was_fallback=False,
                    fallback_reason=None
                )
            else:
                logger.warning(
                    f"LLM returned unparseable response: '{raw_response[:100]}', "
                    "falling back to 'content_safety'"
                )
                return TemplateSelectionResult(
                    template_key="content_safety",
                    was_fallback=True,
                    fallback_reason=f"LLM returned unparseable response: '{raw_response[:50]}...'"
                )

        except TimeoutError:
            logger.error("LLM request timeout during template selection")
            return TemplateSelectionResult(
                template_key="content_safety",
                was_fallback=True,
                fallback_reason="LLM request timeout"
            )
        except Exception as e:
            logger.error(f"Error in auto template selection: {type(e).__name__}: {e}")
            return TemplateSelectionResult(
                template_key="content_safety",
                was_fallback=True,
                fallback_reason=f"LLM error: {type(e).__name__}"
            )

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
            (includes fallback info in metadata if auto mode was used)

        Raises:
            TemplateNotFoundError: If template doesn't exist (manual mode)
            ValueError: If mode is invalid or required fields missing
        """
        # Prepare metadata with mode information
        metadata = request.metadata or {}
        metadata["mode"] = request.mode

        # Determine template key based on mode
        if request.mode == "auto":
            # Auto mode: Use LLM to select best template
            selection_result = await self._auto_select_template(
                user_context=request.user_context,
                instruction=request.instruction
            )
            template_key = selection_result.template_key

            # Include fallback info in metadata (user can see if fallback occurred)
            metadata.update({
                "auto_selected": True,
                "selected_template_key": template_key,
                "was_fallback": selection_result.was_fallback,
            })
            if selection_result.fallback_reason:
                metadata["fallback_reason"] = selection_result.fallback_reason
            if request.instruction:
                metadata["instruction"] = request.instruction
        else:
            # Manual mode: Use user-provided template_key
            template_key = request.template_key
            # Validate template exists
            if not self.template_service.validate_template_key(template_key):
                raise TemplateNotFoundError(template_key)
            metadata["auto_selected"] = False

        # Build guardrail using selected template
        generated_guardrail = self.template_service.build_guardrail(
            template_key=template_key,
            user_context=request.user_context,
            parameters=request.parameters,
        )

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
    ) -> Tuple[List[BatchItemResult], int, int]:
        """
        Generate multiple guardrails at once with per-item error tracking.

        Each item in the result list corresponds to the same index in the
        input requests list, allowing users to easily identify which
        request succeeded or failed.

        Args:
            requests: List of generation requests

        Returns:
            tuple: (list of BatchItemResult, successful count, failed count)
        """
        results = []
        successful = 0
        failed = 0

        for index, request in enumerate(requests):
            try:
                result = await self.generate_guardrail(request)
                results.append(BatchItemResult(
                    index=index,
                    success=True,
                    result=result,
                    error=None,
                    error_type=None
                ))
                successful += 1
            except TemplateNotFoundError as e:
                logger.warning(f"Batch item {index} failed: template not found - {e}")
                results.append(BatchItemResult(
                    index=index,
                    success=False,
                    result=None,
                    error=str(e),
                    error_type="template_not_found"
                ))
                failed += 1
            except ValueError as e:
                logger.warning(f"Batch item {index} failed: validation error - {e}")
                results.append(BatchItemResult(
                    index=index,
                    success=False,
                    result=None,
                    error=str(e),
                    error_type="validation_error"
                ))
                failed += 1
            except TimeoutError as e:
                logger.error(f"Batch item {index} failed: timeout - {e}")
                results.append(BatchItemResult(
                    index=index,
                    success=False,
                    result=None,
                    error="LLM request timeout",
                    error_type="timeout"
                ))
                failed += 1
            except Exception as e:
                logger.error(f"Batch item {index} failed: {type(e).__name__} - {e}")
                results.append(BatchItemResult(
                    index=index,
                    success=False,
                    result=None,
                    error=str(e),
                    error_type=type(e).__name__
                ))
                failed += 1

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
