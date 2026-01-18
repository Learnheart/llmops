"""Prompt composition endpoints - High-level prompt operations."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.schemas import (
    ComposePromptRequest,
    ComposePromptResponse,
)
from app.services.prompt_service import PromptService
from app.templates.registry import TemplateNotFoundError

router = APIRouter(prefix="/prompts")


@router.post("/compose", response_model=ComposePromptResponse)
async def compose_prompt(
    request: ComposePromptRequest,
    db: AsyncSession = Depends(get_db),
):
    """Compose a prompt using a template.

    This is the main entry point for prompt generation.
    - Uses template from CODE to build the prompt
    - Optionally saves the generation to DATABASE

    Args:
        request: Compose request with template_key, agent_instruction, and save flag

    Returns:
        Composed prompt with optional generation_id if saved
    """
    service = PromptService(db)
    try:
        return await service.compose_prompt(request)
    except TemplateNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/batch-compose")
async def batch_compose_prompts(
    requests: list[ComposePromptRequest],
    db: AsyncSession = Depends(get_db),
):
    """Compose multiple prompts in a single request.

    Useful for generating prompts with different templates
    for the same instruction.

    Args:
        requests: List of compose requests

    Returns:
        List of composed prompts
    """
    service = PromptService(db)
    results = []
    errors = []

    for i, request in enumerate(requests):
        try:
            result = await service.compose_prompt(request)
            results.append({
                "index": i,
                "success": True,
                "data": result.model_dump(),
            })
        except TemplateNotFoundError as e:
            errors.append({
                "index": i,
                "success": False,
                "error": str(e),
            })
        except Exception as e:
            errors.append({
                "index": i,
                "success": False,
                "error": f"Unexpected error: {str(e)}",
            })

    return {
        "total": len(requests),
        "successful": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
    }


@router.post("/compare")
async def compare_templates(
    agent_instruction: str,
    template_keys: list[str],
    user_id: str,
    save: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Generate prompts with multiple templates for comparison.

    Useful for evaluating which template works best for a given instruction.

    Args:
        agent_instruction: The instruction to use
        template_keys: List of template keys to compare
        user_id: User ID
        save: Whether to save all generations

    Returns:
        Dictionary of template_key -> generated prompt
    """
    service = PromptService(db)
    results = {}

    for key in template_keys:
        try:
            request = ComposePromptRequest(
                user_id=user_id,
                template_key=key,
                agent_instruction=agent_instruction,
                save=save,
            )
            result = await service.compose_prompt(request)
            results[key] = {
                "template_name": result.template_name,
                "prompt": result.prompt,
                "generation_id": result.generation_id,
                "saved": result.saved,
            }
        except TemplateNotFoundError:
            results[key] = {
                "error": f"Template '{key}' not found",
            }

    return {
        "agent_instruction": agent_instruction,
        "templates_compared": len(template_keys),
        "results": results,
    }
