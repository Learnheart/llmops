"""
Pydantic schemas for request/response validation.
Defines API contracts for the Guardrails Service.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator
from app.models.database import VariantStatus, HistoryAction


# ============================================================================
# Base Schemas
# ============================================================================


class UserRequest(BaseModel):
    """Base schema for all user requests (includes user_id)."""
    user_id: str = Field(..., min_length=1, max_length=255, description="User identifier")


# ============================================================================
# Template Schemas
# ============================================================================


class TemplateInfo(BaseModel):
    """Information about a guardrail template."""
    key: str = Field(..., description="Template unique key")
    name: str = Field(..., description="Human-readable template name")
    description: str = Field(..., description="Template description")


class TemplateDetail(TemplateInfo):
    """Detailed template information including parameters."""
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Template-specific parameters")


class TemplateListResponse(BaseModel):
    """Response containing list of templates."""
    templates: List[TemplateInfo]
    total: int


class PreviewGuardrailRequest(BaseModel):
    """Request to preview a guardrail without saving."""
    user_context: str = Field(..., min_length=1, description="Context for guardrail generation")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Template-specific parameters")


class PreviewGuardrailResponse(BaseModel):
    """Response for guardrail preview."""
    template_key: str
    generated_guardrail: str
    parameters: Optional[Dict[str, Any]] = None


# ============================================================================
# Generation Schemas
# ============================================================================


class GenerateGuardrailRequest(UserRequest):
    """Request to generate a new guardrail with manual or auto template selection."""
    mode: str = Field(
        default="manual",
        description="Generation mode: 'manual' (user selects template) or 'auto' (AI selects best template)"
    )
    template_key: Optional[str] = Field(
        default=None,
        description="Template to use (required for manual mode, ignored in auto mode)"
    )
    user_context: str = Field(..., min_length=1, description="Context for guardrail generation")
    instruction: Optional[str] = Field(
        default=None,
        description="Detailed instruction for auto mode to help AI select the best template"
    )
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Template-specific parameters")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

    @model_validator(mode='after')
    def validate_mode_requirements(self):
        """Validate that required fields are present based on mode."""
        if self.mode not in ["manual", "auto"]:
            raise ValueError("mode must be either 'manual' or 'auto'")

        if self.mode == "manual" and not self.template_key:
            raise ValueError("template_key is required when mode='manual'")

        if self.mode == "auto" and not self.instruction:
            # instruction is optional but recommended for auto mode
            pass

        return self


class GuardrailGenerationResponse(BaseModel):
    """Response for a generated guardrail."""
    id: str
    user_id: str
    template_key: str
    user_context: str
    generated_guardrail: str
    parameters: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ListGenerationsRequest(UserRequest):
    """Request to list generations with pagination."""
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    template_key: Optional[str] = Field(default=None, description="Filter by template key")


class ListGenerationsResponse(BaseModel):
    """Response for listing generations."""
    items: List[GuardrailGenerationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# Variant Schemas
# ============================================================================


class CreateVariantRequest(UserRequest):
    """Request to create a new variant from a generation."""
    generation_id: str = Field(..., description="ID of the generation to create variant from")
    name: str = Field(..., min_length=1, max_length=255, description="Variant name")
    description: Optional[str] = Field(default=None, description="Variant description")
    guardrail_content: Optional[str] = Field(
        default=None,
        description="Custom guardrail content (uses generation's content if not provided)"
    )
    status: Optional[VariantStatus] = Field(default=VariantStatus.DRAFT, description="Initial status")
    tags: Optional[List[str]] = Field(default=None, description="Tags for organization")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class UpdateVariantRequest(UserRequest):
    """Request to create a new version of an existing variant (insert-only, no update)."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255, description="New variant name")
    description: Optional[str] = Field(default=None, description="New description")
    guardrail_content: Optional[str] = Field(default=None, description="Updated guardrail content")
    tags: Optional[List[str]] = Field(default=None, description="Updated tags")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Updated metadata")
    change_summary: Optional[str] = Field(default=None, description="Summary of changes made")


class SetVariantStatusRequest(UserRequest):
    """Request to change variant status."""
    status: VariantStatus = Field(..., description="New status")


class SetVariantActiveRequest(UserRequest):
    """Request to activate/deactivate a variant."""
    is_active: bool = Field(..., description="Active state")


class GuardrailVariantResponse(BaseModel):
    """Response for a guardrail variant."""
    id: str
    generation_id: str
    user_id: str
    name: str
    description: Optional[str] = None
    guardrail_content: str
    version: int
    is_active: bool
    status: VariantStatus
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ListVariantsRequest(UserRequest):
    """Request to list variants with pagination and filters."""
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    generation_id: Optional[str] = Field(default=None, description="Filter by generation ID")
    status: Optional[VariantStatus] = Field(default=None, description="Filter by status")
    is_active: Optional[bool] = Field(default=None, description="Filter by active state")
    tags: Optional[List[str]] = Field(default=None, description="Filter by tags (any match)")


class ListVariantsResponse(BaseModel):
    """Response for listing variants."""
    items: List[GuardrailVariantResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# History Schemas
# ============================================================================


class GuardrailVariantHistoryResponse(BaseModel):
    """Response for variant history entry."""
    id: str
    variant_id: str
    user_id: str
    action: HistoryAction
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    old_version: Optional[int] = None
    new_version: Optional[int] = None
    old_status: Optional[VariantStatus] = None
    new_status: Optional[VariantStatus] = None
    change_summary: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ListHistoryRequest(UserRequest):
    """Request to list variant history with pagination."""
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


class ListHistoryResponse(BaseModel):
    """Response for listing variant history."""
    items: List[GuardrailVariantHistoryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# Batch Operation Schemas
# ============================================================================


class BatchGenerateRequest(UserRequest):
    """Request to generate multiple guardrails at once."""
    generations: List[GenerateGuardrailRequest] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of generation requests (max 10)"
    )


class BatchGenerateResponse(BaseModel):
    """Response for batch generation."""
    results: List[GuardrailGenerationResponse]
    total: int
    successful: int
    failed: int


# ============================================================================
# Comparison Schemas
# ============================================================================


class CompareTemplatesRequest(UserRequest):
    """Request to compare multiple templates with same context."""
    template_keys: List[str] = Field(
        ...,
        min_length=2,
        max_length=5,
        description="Template keys to compare (2-5 templates)"
    )
    user_context: str = Field(..., min_length=1, description="Context for all templates")
    parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Common parameters for all templates"
    )


class TemplateComparisonResult(BaseModel):
    """Result for a single template in comparison."""
    template_key: str
    template_name: str
    generated_guardrail: str
    parameters: Optional[Dict[str, Any]] = None


class CompareTemplatesResponse(BaseModel):
    """Response for template comparison."""
    user_context: str
    comparisons: List[TemplateComparisonResult]
    total: int


# ============================================================================
# Health Check Schemas
# ============================================================================


class HealthCheckResponse(BaseModel):
    """Response for health check endpoint."""
    status: str = Field(..., description="Service status (healthy/unhealthy)")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(..., description="Current server time")


class DetailedHealthCheckResponse(HealthCheckResponse):
    """Detailed health check with component status."""
    database: Dict[str, Any] = Field(..., description="Database connection status")
    dependencies: Dict[str, Any] = Field(default_factory=dict, description="External dependencies status")
