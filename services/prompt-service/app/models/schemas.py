"""Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict

from app.models.database import VariantStatus, HistoryAction


# =============================================================================
# Base Schemas
# =============================================================================

class UserRequest(BaseModel):
    """Base schema with user_id for all requests."""
    user_id: str = Field(..., min_length=1, max_length=255, description="User identifier")


# =============================================================================
# Template Schemas
# =============================================================================

class TemplateInfo(BaseModel):
    """Template information response."""
    key: str
    name: str
    description: str

    model_config = ConfigDict(from_attributes=True)


class TemplateListResponse(BaseModel):
    """Response for listing templates."""
    templates: List[TemplateInfo]
    count: int


# =============================================================================
# Generation Schemas
# =============================================================================

class GeneratePromptRequest(UserRequest):
    """Request to generate a prompt."""
    template_key: str = Field(..., min_length=1, max_length=100)
    agent_instruction: str = Field(..., min_length=1)
    metadata: Optional[dict] = Field(default=None)


class PromptGenerationResponse(BaseModel):
    """Response for a generated prompt."""
    id: str
    user_id: str
    template_key: str
    agent_instruction: str
    generated_prompt: str
    metadata: Optional[dict] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GenerationListResponse(BaseModel):
    """Response for listing generations."""
    generations: List[PromptGenerationResponse]
    count: int
    page: int
    page_size: int
    total_pages: int


# =============================================================================
# Variant Schemas
# =============================================================================

class CreateVariantRequest(UserRequest):
    """Request to create a variant from a generation."""
    generation_id: str = Field(..., description="ID of the source generation")
    name: str = Field(..., min_length=1, max_length=255)
    prompt_content: Optional[str] = Field(
        default=None,
        description="Custom prompt content. If not provided, uses generation's prompt."
    )
    metadata: Optional[dict] = Field(default=None)


class UpdateVariantRequest(UserRequest):
    """Request to update a variant (creates new version)."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    prompt_content: Optional[str] = Field(default=None, min_length=1)
    metadata: Optional[dict] = Field(default=None)
    change_summary: Optional[str] = Field(
        default=None,
        description="Summary of changes for audit log"
    )


class ActivateVariantRequest(UserRequest):
    """Request to activate/deactivate a variant."""
    is_active: bool = Field(..., description="Whether to activate or deactivate")


class ChangeVariantStatusRequest(UserRequest):
    """Request to change variant status."""
    status: VariantStatus = Field(..., description="New status")


class PromptVariantResponse(BaseModel):
    """Response for a prompt variant."""
    id: str
    generation_id: str
    user_id: str
    name: str
    prompt_content: str
    version: int
    is_active: bool
    status: VariantStatus
    metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VariantListResponse(BaseModel):
    """Response for listing variants."""
    variants: List[PromptVariantResponse]
    count: int
    page: int
    page_size: int
    total_pages: int


# =============================================================================
# History Schemas
# =============================================================================

class VariantHistoryResponse(BaseModel):
    """Response for variant history entry."""
    id: str
    variant_id: str
    user_id: str
    action: HistoryAction
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    old_version: Optional[int] = None
    new_version: Optional[int] = None
    change_summary: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HistoryListResponse(BaseModel):
    """Response for listing history."""
    history: List[VariantHistoryResponse]
    count: int


# =============================================================================
# Prompt Composition Schemas
# =============================================================================

class ComposePromptRequest(UserRequest):
    """Request to compose a prompt using a template."""
    template_key: str = Field(..., min_length=1, max_length=100)
    agent_instruction: str = Field(..., min_length=1)
    save: bool = Field(default=True, description="Whether to save the generation")
    metadata: Optional[dict] = Field(default=None)


class ComposePromptResponse(BaseModel):
    """Response for prompt composition."""
    prompt: str
    template_key: str
    template_name: str
    generation_id: Optional[str] = None
    saved: bool


# =============================================================================
# Health Schemas
# =============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
    database: str


class DetailedHealthResponse(HealthResponse):
    """Detailed health check response."""
    uptime: float
    database_latency_ms: Optional[float] = None


# =============================================================================
# Error Schemas
# =============================================================================

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class ValidationErrorResponse(BaseModel):
    """Validation error response."""
    error: str = "Validation Error"
    detail: List[dict]
