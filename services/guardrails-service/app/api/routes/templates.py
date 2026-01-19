"""
Template endpoints for listing and previewing guardrail templates.
Templates are read-only and loaded from code (not database).
"""

from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    TemplateDetail,
    TemplateListResponse,
    PreviewGuardrailRequest,
    PreviewGuardrailResponse,
)
from app.services.template_service import TemplateService
from app.templates.registry import TemplateNotFoundError

router = APIRouter()
template_service = TemplateService()


@router.get("/templates", response_model=TemplateListResponse, tags=["templates"])
async def list_templates():
    """
    Get all available guardrail templates.

    Returns:
        TemplateListResponse: List of all templates with metadata
    """
    templates = template_service.list_all_templates()
    return TemplateListResponse(
        templates=templates,
        total=len(templates),
    )


@router.get("/templates/keys", response_model=list[str], tags=["templates"])
async def get_template_keys():
    """
    Get all template keys.

    Returns:
        List[str]: List of template keys
    """
    return template_service.get_template_keys()


@router.get("/templates/{template_key}", response_model=TemplateDetail, tags=["templates"])
async def get_template(template_key: str):
    """
    Get detailed information about a specific template.

    Args:
        template_key: Template key (e.g., 'content_safety', 'pii_protection')

    Returns:
        TemplateDetail: Template details including parameters

    Raises:
        HTTPException: 404 if template not found
    """
    try:
        template_info = template_service.get_template_info(template_key)
        return TemplateDetail(**template_info)
    except TemplateNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/templates/{template_key}/preview", response_model=PreviewGuardrailResponse, tags=["templates"])
async def preview_template(template_key: str, request: PreviewGuardrailRequest):
    """
    Preview a guardrail without saving to database.

    This endpoint allows users to test a template before generating
    and saving a guardrail.

    Args:
        template_key: Template key to preview
        request: Preview request with context and parameters

    Returns:
        PreviewGuardrailResponse: Preview with generated guardrail

    Raises:
        HTTPException: 404 if template not found
        HTTPException: 400 if generation fails
    """
    try:
        preview = template_service.preview_guardrail(
            template_key=template_key,
            user_context=request.user_context,
            parameters=request.parameters,
        )
        return PreviewGuardrailResponse(
            template_key=preview["template_key"],
            generated_guardrail=preview["generated_guardrail"],
            parameters=preview["parameters"],
        )
    except TemplateNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Preview generation failed: {str(e)}")
