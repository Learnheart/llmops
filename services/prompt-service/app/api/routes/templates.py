"""Template endpoints - Read-only access to prompt templates from CODE."""

from fastapi import APIRouter, HTTPException

from app.models.schemas import TemplateInfo, TemplateListResponse
from app.services.template_service import TemplateService
from app.templates.registry import TemplateNotFoundError

router = APIRouter(prefix="/templates")

# Initialize service (templates are in code, no DB needed)
template_service = TemplateService()


@router.get("", response_model=TemplateListResponse)
async def list_templates():
    """List all available prompt templates.

    Templates are defined in code and managed by developers.
    """
    templates = template_service.list_templates()
    return TemplateListResponse(
        templates=templates,
        count=len(templates),
    )


@router.get("/keys")
async def list_template_keys():
    """Get list of available template keys."""
    keys = template_service.get_template_keys()
    return {"keys": keys, "count": len(keys)}


@router.get("/{template_key}", response_model=TemplateInfo)
async def get_template(template_key: str):
    """Get details of a specific template.

    Args:
        template_key: The template key (e.g., "concise", "detailed")
    """
    template_info = template_service.get_template_info(template_key)
    if not template_info:
        raise HTTPException(
            status_code=404,
            detail=f"Template '{template_key}' not found",
        )
    return template_info


@router.post("/{template_key}/preview")
async def preview_template(template_key: str, agent_instruction: str):
    """Preview a prompt generated with a template.

    This does NOT save the generation - use /prompts/compose for that.

    Args:
        template_key: The template key
        agent_instruction: The instruction to incorporate
    """
    try:
        prompt = template_service.build_prompt(template_key, agent_instruction)
        template_info = template_service.get_template_info(template_key)
        return {
            "template_key": template_key,
            "template_name": template_info.name if template_info else template_key,
            "agent_instruction": agent_instruction,
            "preview": prompt,
        }
    except TemplateNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
