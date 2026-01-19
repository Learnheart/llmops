# File Contents Collection
Generated: 2026-01-19 10:38:45.979085


## Directory: services/guardrails-service

### File: app/__init__.py
```

```
==================================================

### File: app/api/__init__.py
```

```
==================================================

### File: app/api/routes/__init__.py
```

```
==================================================

### File: app/api/routes/generations.py
```
"""
Generation endpoints for creating and managing guardrail generations.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.schemas import (
    GenerateGuardrailRequest,
    GuardrailGenerationResponse,
    ListGenerationsRequest,
    ListGenerationsResponse,
)
from app.services.guardrail_service import GuardrailService
from app.templates.registry import TemplateNotFoundError

router = APIRouter()


@router.post("", response_model=GuardrailGenerationResponse, status_code=201, tags=["generations"])
async def generate_guardrail(
    request: GenerateGuardrailRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a new guardrail and save to database.

    Creates a guardrail using the specified template and saves it for
    future reference and variant creation.

    Args:
        request: Generation request with template, context, and parameters
        db: Database session dependency

    Returns:
        GuardrailGenerationResponse: Generated guardrail information

    Raises:
        HTTPException: 400 if template not found
        HTTPException: 500 if generation fails
    """
    service = GuardrailService(db)
    try:
        return await service.generate_guardrail(request)
    except TemplateNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.get("", response_model=ListGenerationsResponse, tags=["generations"])
async def list_generations(
    user_id: str,
    page: int = 1,
    page_size: int = 20,
    template_key: str = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List guardrail generations for a user with pagination.

    Args:
        user_id: User ID for filtering
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100)
        template_key: Optional template key filter
        db: Database session dependency

    Returns:
        ListGenerationsResponse: Paginated list of generations

    Raises:
        HTTPException: 400 if pagination parameters invalid
    """
    if page < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=400,
            detail="Invalid pagination parameters. Page must be >= 1, page_size between 1-100"
        )

    service = GuardrailService(db)
    try:
        items, total = await service.list_generations(
            user_id=user_id,
            page=page,
            page_size=page_size,
            template_key=template_key,
        )

        total_pages = (total + page_size - 1) // page_size

        return ListGenerationsResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list generations: {str(e)}")


@router.get("/{generation_id}", response_model=GuardrailGenerationResponse, tags=["generations"])
async def get_generation(
    generation_id: UUID,
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific guardrail generation by ID.

    Args:
        generation_id: Generation UUID
        user_id: User ID for access control
        db: Database session dependency

    Returns:
        GuardrailGenerationResponse: Generation details

    Raises:
        HTTPException: 404 if generation not found or access denied
    """
    service = GuardrailService(db)
    generation = await service.get_generation(generation_id, user_id)

    if not generation:
        raise HTTPException(
            status_code=404,
            detail=f"Generation '{generation_id}' not found or access denied"
        )

    return generation


@router.delete("/{generation_id}", status_code=204, tags=["generations"])
async def delete_generation(
    generation_id: UUID,
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a guardrail generation.

    This will also delete all associated variants due to cascade delete.

    Args:
        generation_id: Generation UUID
        user_id: User ID for access control
        db: Database session dependency

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: 404 if generation not found or access denied
    """
    service = GuardrailService(db)
    deleted = await service.delete_generation(generation_id, user_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Generation '{generation_id}' not found or access denied"
        )

    return None

```
==================================================

### File: app/api/routes/guardrails.py
```
"""
High-level guardrail endpoints for composition and comparison.
These are convenience endpoints that combine multiple operations.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.schemas import (
    CompareTemplatesRequest,
    CompareTemplatesResponse,
    TemplateComparisonResult,
    BatchGenerateRequest,
    BatchGenerateResponse,
)
from app.services.guardrail_service import GuardrailService
from app.templates.registry import TemplateNotFoundError

router = APIRouter()


@router.post("/compare", response_model=CompareTemplatesResponse, tags=["guardrails"])
async def compare_templates(
    request: CompareTemplatesRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Compare multiple guardrail templates with the same context.

    This endpoint allows users to generate guardrails using multiple
    templates simultaneously to compare their outputs.

    Args:
        request: Comparison request with template keys and context
        db: Database session dependency

    Returns:
        CompareTemplatesResponse: Comparison results for all templates

    Raises:
        HTTPException: 400 if any template not found
        HTTPException: 400 if invalid number of templates (must be 2-5)
    """
    if len(request.template_keys) < 2 or len(request.template_keys) > 5:
        raise HTTPException(
            status_code=400,
            detail="Must compare between 2 and 5 templates"
        )

    service = GuardrailService(db)
    try:
        comparisons = await service.compare_templates(request)

        return CompareTemplatesResponse(
            user_context=request.user_context,
            comparisons=comparisons,
            total=len(comparisons),
        )
    except TemplateNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@router.post("/batch", response_model=BatchGenerateResponse, tags=["guardrails"])
async def batch_generate(
    request: BatchGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate multiple guardrails in a single request.

    Useful for bulk generation operations. Failed generations are
    skipped and reported in the response.

    Args:
        request: Batch generation request (max 10 generations)
        db: Database session dependency

    Returns:
        BatchGenerateResponse: Results with success/failure counts

    Raises:
        HTTPException: 400 if invalid number of requests (must be 1-10)
    """
    if len(request.generations) < 1 or len(request.generations) > 10:
        raise HTTPException(
            status_code=400,
            detail="Must provide between 1 and 10 generation requests"
        )

    service = GuardrailService(db)
    try:
        results, successful, failed = await service.batch_generate(request.generations)

        return BatchGenerateResponse(
            results=results,
            total=len(request.generations),
            successful=successful,
            failed=failed,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch generation failed: {str(e)}")

```
==================================================

### File: app/api/routes/health.py
```
"""
Health check endpoints for monitoring and readiness probes.
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.database import get_db
from app.models.schemas import HealthCheckResponse, DetailedHealthCheckResponse

router = APIRouter()
settings = get_settings()


@router.get("/health", response_model=HealthCheckResponse, tags=["health"])
async def health_check():
    """
    Basic health check endpoint.

    Returns:
        HealthCheckResponse: Service health status
    """
    return HealthCheckResponse(
        status="healthy",
        service=settings.service_name,
        version="0.1.0",
        timestamp=datetime.utcnow(),
    )


@router.get("/health/detailed", response_model=DetailedHealthCheckResponse, tags=["health"])
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """
    Detailed health check including database connectivity.

    Args:
        db: Database session dependency

    Returns:
        DetailedHealthCheckResponse: Detailed health status
    """
    # Check database
    db_status = {"status": "unknown", "latency_ms": None}
    try:
        start_time = datetime.utcnow()
        await db.execute(text("SELECT 1"))
        end_time = datetime.utcnow()
        latency_ms = (end_time - start_time).total_seconds() * 1000

        db_status = {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
        }
    except Exception as e:
        db_status = {
            "status": "unhealthy",
            "error": str(e),
        }

    overall_status = "healthy" if db_status["status"] == "healthy" else "unhealthy"

    return DetailedHealthCheckResponse(
        status=overall_status,
        service=settings.service_name,
        version="0.1.0",
        timestamp=datetime.utcnow(),
        database=db_status,
        dependencies={},
    )


@router.get("/ready", tags=["health"])
async def readiness_probe(db: AsyncSession = Depends(get_db)):
    """
    Kubernetes readiness probe.

    Checks if the service is ready to accept traffic.

    Args:
        db: Database session dependency

    Returns:
        dict: Readiness status
    """
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        return {"status": "not ready", "error": str(e)}


@router.get("/live", tags=["health"])
async def liveness_probe():
    """
    Kubernetes liveness probe.

    Checks if the service is alive.

    Returns:
        dict: Liveness status
    """
    return {"status": "alive"}

```
==================================================

### File: app/api/routes/templates.py
```
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

```
==================================================

### File: app/api/routes/variants.py
```
"""
Variant endpoints for managing guardrail variants with versioning.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db, VariantStatus
from app.models.schemas import (
    CreateVariantRequest,
    UpdateVariantRequest,
    GuardrailVariantResponse,
    ListVariantsRequest,
    ListVariantsResponse,
    SetVariantStatusRequest,
    SetVariantActiveRequest,
    ListHistoryRequest,
    ListHistoryResponse,
)
from app.services.variant_service import (
    VariantService,
    VariantNotFoundError,
    GenerationNotFoundError,
)

router = APIRouter()


@router.post("", response_model=GuardrailVariantResponse, status_code=201, tags=["variants"])
async def create_variant(
    request: CreateVariantRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new guardrail variant from a generation.

    Variants allow users to customize and save specific versions of guardrails.

    Args:
        request: Variant creation request
        db: Database session dependency

    Returns:
        GuardrailVariantResponse: Created variant with version 1

    Raises:
        HTTPException: 404 if generation not found
        HTTPException: 500 if creation fails
    """
    service = VariantService(db)
    try:
        return await service.create_variant(request)
    except GenerationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Variant creation failed: {str(e)}")


@router.get("", response_model=ListVariantsResponse, tags=["variants"])
async def list_variants(
    user_id: str,
    page: int = 1,
    page_size: int = 20,
    generation_id: str = None,
    status: VariantStatus = None,
    is_active: bool = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List guardrail variants for a user with pagination and filters.

    Args:
        user_id: User ID for filtering
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100)
        generation_id: Optional generation ID filter
        status: Optional status filter (draft, active, archived)
        is_active: Optional active state filter
        db: Database session dependency

    Returns:
        ListVariantsResponse: Paginated list of variants

    Raises:
        HTTPException: 400 if pagination parameters invalid
    """
    if page < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=400,
            detail="Invalid pagination parameters. Page must be >= 1, page_size between 1-100"
        )

    service = VariantService(db)
    try:
        generation_uuid = UUID(generation_id) if generation_id else None

        items, total = await service.list_variants(
            user_id=user_id,
            page=page,
            page_size=page_size,
            generation_id=generation_uuid,
            status=status,
            is_active=is_active,
        )

        total_pages = (total + page_size - 1) // page_size

        return ListVariantsResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list variants: {str(e)}")


@router.get("/{variant_id}", response_model=GuardrailVariantResponse, tags=["variants"])
async def get_variant(
    variant_id: UUID,
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific guardrail variant by ID.

    Args:
        variant_id: Variant UUID
        user_id: User ID for access control
        db: Database session dependency

    Returns:
        GuardrailVariantResponse: Variant details

    Raises:
        HTTPException: 404 if variant not found or access denied
    """
    service = VariantService(db)
    variant = await service.get_variant(variant_id, user_id)

    if not variant:
        raise HTTPException(
            status_code=404,
            detail=f"Variant '{variant_id}' not found or access denied"
        )

    return variant


@router.post("/{variant_id}/versions", response_model=GuardrailVariantResponse, status_code=201, tags=["variants"])
async def create_new_version(
    variant_id: UUID,
    request: UpdateVariantRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new version of a guardrail variant.

    This follows the "insert-only" principle - instead of updating the existing variant,
    a new version is created. The old version remains unchanged for audit purposes.

    Args:
        variant_id: Source variant UUID (will create new version from this)
        request: New version request with updated content
        db: Database session dependency

    Returns:
        GuardrailVariantResponse: Newly created variant with incremented version

    Raises:
        HTTPException: 404 if source variant not found or access denied
        HTTPException: 500 if version creation fails
    """
    service = VariantService(db)
    try:
        return await service.create_new_version(variant_id, request)
    except VariantNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Version creation failed: {str(e)}")


@router.post("/{variant_id}/activate", response_model=GuardrailVariantResponse, tags=["variants"])
async def set_variant_active(
    variant_id: UUID,
    request: SetVariantActiveRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Activate or deactivate a guardrail variant.

    Args:
        variant_id: Variant UUID
        request: Activation request
        db: Database session dependency

    Returns:
        GuardrailVariantResponse: Updated variant

    Raises:
        HTTPException: 404 if variant not found or access denied
        HTTPException: 500 if operation fails
    """
    service = VariantService(db)
    try:
        return await service.set_variant_active(variant_id, request)
    except VariantNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Activation failed: {str(e)}")


@router.post("/{variant_id}/status", response_model=GuardrailVariantResponse, tags=["variants"])
async def set_variant_status(
    variant_id: UUID,
    request: SetVariantStatusRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Change the status of a guardrail variant.

    Status can be: draft, active, or archived.

    Args:
        variant_id: Variant UUID
        request: Status change request
        db: Database session dependency

    Returns:
        GuardrailVariantResponse: Updated variant

    Raises:
        HTTPException: 404 if variant not found or access denied
        HTTPException: 500 if operation fails
    """
    service = VariantService(db)
    try:
        return await service.set_variant_status(variant_id, request)
    except VariantNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status change failed: {str(e)}")


@router.delete("/{variant_id}", status_code=204, tags=["variants"])
async def delete_variant(
    variant_id: UUID,
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a guardrail variant.

    This will also delete all associated history entries.

    Args:
        variant_id: Variant UUID
        user_id: User ID for access control
        db: Database session dependency

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: 404 if variant not found or access denied
    """
    service = VariantService(db)
    deleted = await service.delete_variant(variant_id, user_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Variant '{variant_id}' not found or access denied"
        )

    return None


@router.get("/{variant_id}/history", response_model=ListHistoryResponse, tags=["variants"])
async def get_variant_history(
    variant_id: UUID,
    user_id: str,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the change history for a variant.

    Shows all changes, updates, and status changes with full audit trail.

    Args:
        variant_id: Variant UUID
        user_id: User ID for access control
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100)
        db: Database session dependency

    Returns:
        ListHistoryResponse: Paginated history entries

    Raises:
        HTTPException: 404 if variant not found or access denied
        HTTPException: 400 if pagination parameters invalid
    """
    if page < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=400,
            detail="Invalid pagination parameters. Page must be >= 1, page_size between 1-100"
        )

    service = VariantService(db)
    try:
        items, total = await service.get_variant_history(
            variant_id=variant_id,
            user_id=user_id,
            page=page,
            page_size=page_size,
        )

        total_pages = (total + page_size - 1) // page_size

        return ListHistoryResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    except VariantNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")

```
==================================================

### File: app/config.py
```
"""
Configuration management for Guardrails Service.
Loads settings from environment variables with fallback to .env file.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Service Configuration
    service_name: str = "guardrails-service"
    service_port: int = 8083
    log_level: str = "INFO"
    environment: str = "development"

    # PostgreSQL Database Configuration
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "llmops"
    postgres_password: str = ""
    postgres_db: str = "llmops"

    # Database Connection Pool Settings
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_pre_ping: bool = True
    db_echo: bool = False

    # LLM Provider Configuration
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    groq_api_key: str = ""
    default_llm_provider: str = "groq"

    # LLM Model Configuration
    default_model: str = "llama-3.3-70b-versatile"
    default_temperature: float = 0.7
    default_max_tokens: int = 2000

    # API Configuration
    api_v1_prefix: str = "/api/v1"
    cors_origins: list = ["*"]

    # Message Queue Configuration (NATS)
    nats_url: str = "nats://nats:4222"
    nats_max_reconnect_attempts: int = 60
    nats_reconnect_time_wait: int = 2

    # Elasticsearch Configuration
    elasticsearch_url: str = "http://elasticsearch:9200"
    elasticsearch_index_prefix: str = "guardrails"

    # Pagination
    default_page_size: int = 20
    max_page_size: int = 100

    @property
    def database_url(self) -> str:
        """Construct async PostgreSQL database URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        """Construct sync PostgreSQL database URL (for migrations)."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to ensure single instance across application.
    """
    return Settings()

```
==================================================

### File: app/main.py
```
"""
Main FastAPI application for Guardrails Service.
Entry point for the service with router configuration and lifecycle management.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models.database import init_db, close_db
from app.api.routes import health, templates, generations, variants, guardrails


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    print(f"Starting {settings.service_name}...")
    await init_db()
    print("Database initialized successfully")

    yield

    # Shutdown
    print(f"Shutting down {settings.service_name}...")
    await close_db()
    print("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title="Guardrails Service",
    description="""
    LLMOps Platform - Guardrails Service

    This service provides guardrail templates and management capabilities for LLM applications.
    Guardrails help ensure safe, compliant, and high-quality AI interactions.

    ## Features

    * **Template Library**: Pre-built guardrail templates for common use cases
    * **Custom Guardrails**: Generate guardrails from templates with custom parameters
    * **Variant Management**: Save and version customized guardrails
    * **History Tracking**: Complete audit trail for all changes
    * **Stateless Design**: No user data storage, only guardrail definitions

    ## Available Templates

    * **Content Safety**: Prevent harmful or inappropriate content
    * **PII Protection**: Protect personally identifiable information
    * **Factual Accuracy**: Ensure accuracy and prevent hallucinations
    * **Tone Control**: Maintain appropriate communication style
    * **Compliance**: Ensure regulatory compliance (GDPR, HIPAA, etc.)

    ## Quick Start

    1. Browse available templates: `GET /api/v1/templates`
    2. Preview a template: `POST /api/v1/templates/{key}/preview`
    3. Generate a guardrail: `POST /api/v1/generations`
    4. Create a variant: `POST /api/v1/variants`
    5. Manage variants: Update, activate, archive as needed

    ## API Organization

    * `/health` - Health check and monitoring endpoints
    * `/api/v1/templates` - Template browsing and preview (read-only)
    * `/api/v1/generations` - Guardrail generation CRUD
    * `/api/v1/variants` - Variant management with versioning
    * `/api/v1/guardrails` - High-level composition and comparison
    """,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers

# Health check endpoints (no prefix)
app.include_router(
    health.router,
    tags=["health"],
)

# API v1 endpoints
app.include_router(
    templates.router,
    prefix=f"{settings.api_v1_prefix}",
    tags=["templates"],
)

app.include_router(
    generations.router,
    prefix=f"{settings.api_v1_prefix}/generations",
    tags=["generations"],
)

app.include_router(
    variants.router,
    prefix=f"{settings.api_v1_prefix}/variants",
    tags=["variants"],
)

app.include_router(
    guardrails.router,
    prefix=f"{settings.api_v1_prefix}/guardrails",
    tags=["guardrails"],
)


@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint with service information.

    Returns:
        dict: Service information and links
    """
    return {
        "service": settings.service_name,
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "api_version": "v1",
        "endpoints": {
            "templates": f"{settings.api_v1_prefix}/templates",
            "generations": f"{settings.api_v1_prefix}/generations",
            "variants": f"{settings.api_v1_prefix}/variants",
            "guardrails": f"{settings.api_v1_prefix}/guardrails",
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )

```
==================================================

### File: app/models/__init__.py
```

```
==================================================

### File: app/models/database.py
```
"""
SQLAlchemy ORM models for Guardrails Service.
Defines database schema for guardrail generations, variants, and history.
"""

import enum
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncAttrs, create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, relationship
from app.config import get_settings


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all database models."""
    pass


class VariantStatus(str, enum.Enum):
    """Status of a guardrail variant."""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class HistoryAction(str, enum.Enum):
    """Types of actions that can be logged in history."""
    CREATED = "created"
    UPDATED = "updated"
    ACTIVATED = "activated"
    DEACTIVATED = "deactivated"
    ARCHIVED = "archived"
    STATUS_CHANGED = "status_changed"


class GuardrailGeneration(Base):
    """
    Stores generated guardrails from templates.

    This is the output of applying a guardrail template with specific parameters.
    It represents a single guardrail generation that can be used or customized.
    """
    __tablename__ = "guardrail_generations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    template_key = Column(String(100), nullable=False, index=True)
    user_context = Column(Text, nullable=False)
    generated_guardrail = Column(Text, nullable=False)
    parameters = Column(JSON, nullable=True)  # Template-specific parameters
    metadata = Column(JSON, nullable=True)  # Additional metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    variants = relationship(
        "GuardrailVariant",
        back_populates="generation",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<GuardrailGeneration(id={self.id}, template={self.template_key}, user={self.user_id})>"


class GuardrailVariant(Base):
    """
    User-customized guardrails with versioning support.

    Variants allow users to customize and save specific versions of guardrails.
    Each update creates a new version, maintaining a complete history.
    """
    __tablename__ = "guardrail_variants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    generation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("guardrail_generations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    guardrail_content = Column(Text, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    status = Column(
        Enum(VariantStatus),
        default=VariantStatus.DRAFT,
        nullable=False,
        index=True,
    )
    tags = Column(JSON, nullable=True)  # User-defined tags for organization
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    generation = relationship("GuardrailGeneration", back_populates="variants")
    history = relationship(
        "GuardrailVariantHistory",
        back_populates="variant",
        cascade="all, delete-orphan",
        order_by="GuardrailVariantHistory.created_at.desc()",
    )

    def __repr__(self):
        return f"<GuardrailVariant(id={self.id}, name={self.name}, version={self.version}, status={self.status})>"


class GuardrailVariantHistory(Base):
    """
    Audit log for all guardrail variant changes.

    Maintains a complete history of all changes to variants for compliance,
    debugging, and rollback capabilities.
    """
    __tablename__ = "guardrail_variant_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    variant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("guardrail_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(String(255), nullable=False, index=True)
    action = Column(Enum(HistoryAction), nullable=False)
    old_content = Column(Text, nullable=True)
    new_content = Column(Text, nullable=True)
    old_version = Column(Integer, nullable=True)
    new_version = Column(Integer, nullable=True)
    old_status = Column(Enum(VariantStatus), nullable=True)
    new_status = Column(Enum(VariantStatus), nullable=True)
    change_summary = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    variant = relationship("GuardrailVariant", back_populates="history")

    def __repr__(self):
        return f"<GuardrailVariantHistory(id={self.id}, variant={self.variant_id}, action={self.action})>"


# Database engine and session management
settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
    pool_pre_ping=settings.db_pool_pre_ping,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """
    Dependency for getting database sessions.

    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """
    Initialize database tables.
    Creates all tables defined in Base metadata.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """
    Close database connections.
    Call during application shutdown.
    """
    await engine.dispose()

```
==================================================

### File: app/models/schemas.py
```
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

```
==================================================

### File: app/repositories/__init__.py
```

```
==================================================

### File: app/repositories/generation_repository.py
```
"""
Repository for GuardrailGeneration CRUD operations.
Handles database access for guardrail generations.
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import GuardrailGeneration


class GenerationRepository:
    """Repository for managing guardrail generations in the database."""

    def __init__(self, db: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            db: Async database session
        """
        self.db = db

    async def create(
        self,
        user_id: str,
        template_key: str,
        user_context: str,
        generated_guardrail: str,
        parameters: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> GuardrailGeneration:
        """
        Create a new guardrail generation.

        Args:
            user_id: ID of the user creating the generation
            template_key: Key of the template used
            user_context: User-provided context
            generated_guardrail: Generated guardrail content
            parameters: Template parameters used
            metadata: Additional metadata

        Returns:
            GuardrailGeneration: Created generation instance
        """
        generation = GuardrailGeneration(
            user_id=user_id,
            template_key=template_key,
            user_context=user_context,
            generated_guardrail=generated_guardrail,
            parameters=parameters,
            metadata=metadata,
        )
        self.db.add(generation)
        await self.db.commit()
        await self.db.refresh(generation)
        return generation

    async def get_by_id(self, generation_id: UUID) -> Optional[GuardrailGeneration]:
        """
        Get a generation by ID.

        Args:
            generation_id: Generation UUID

        Returns:
            Optional[GuardrailGeneration]: Generation if found, None otherwise
        """
        result = await self.db.execute(
            select(GuardrailGeneration).where(GuardrailGeneration.id == generation_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_user(
        self, generation_id: UUID, user_id: str
    ) -> Optional[GuardrailGeneration]:
        """
        Get a generation by ID and user (for access control).

        Args:
            generation_id: Generation UUID
            user_id: User ID

        Returns:
            Optional[GuardrailGeneration]: Generation if found and belongs to user, None otherwise
        """
        result = await self.db.execute(
            select(GuardrailGeneration).where(
                GuardrailGeneration.id == generation_id,
                GuardrailGeneration.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        template_key: Optional[str] = None,
    ) -> tuple[List[GuardrailGeneration], int]:
        """
        List generations for a user with pagination and filtering.

        Args:
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Number of items per page
            template_key: Optional template key filter

        Returns:
            tuple: (list of generations, total count)
        """
        # Build query
        query = select(GuardrailGeneration).where(GuardrailGeneration.user_id == user_id)

        if template_key:
            query = query.where(GuardrailGeneration.template_key == template_key)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Apply pagination and ordering
        query = (
            query.order_by(GuardrailGeneration.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def delete(self, generation_id: UUID) -> bool:
        """
        Delete a generation.

        Args:
            generation_id: Generation UUID

        Returns:
            bool: True if deleted, False if not found
        """
        generation = await self.get_by_id(generation_id)
        if not generation:
            return False

        await self.db.delete(generation)
        await self.db.commit()
        return True

    async def delete_by_user(self, generation_id: UUID, user_id: str) -> bool:
        """
        Delete a generation (user-scoped for access control).

        Args:
            generation_id: Generation UUID
            user_id: User ID

        Returns:
            bool: True if deleted, False if not found or access denied
        """
        generation = await self.get_by_id_and_user(generation_id, user_id)
        if not generation:
            return False

        await self.db.delete(generation)
        await self.db.commit()
        return True

    async def count_by_user(self, user_id: str, template_key: Optional[str] = None) -> int:
        """
        Count generations for a user.

        Args:
            user_id: User ID
            template_key: Optional template key filter

        Returns:
            int: Number of generations
        """
        query = select(func.count()).where(GuardrailGeneration.user_id == user_id)

        if template_key:
            query = query.where(GuardrailGeneration.template_key == template_key)

        result = await self.db.execute(query)
        return result.scalar_one()

    async def get_recent_by_template(
        self, user_id: str, template_key: str, limit: int = 5
    ) -> List[GuardrailGeneration]:
        """
        Get recent generations for a specific template.

        Args:
            user_id: User ID
            template_key: Template key
            limit: Maximum number of results

        Returns:
            List[GuardrailGeneration]: Recent generations
        """
        query = (
            select(GuardrailGeneration)
            .where(
                GuardrailGeneration.user_id == user_id,
                GuardrailGeneration.template_key == template_key,
            )
            .order_by(GuardrailGeneration.created_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

```
==================================================

### File: app/repositories/history_repository.py
```
"""
Repository for GuardrailVariantHistory operations.
Handles audit logging for all variant changes.
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import GuardrailVariantHistory, HistoryAction, VariantStatus


class HistoryRepository:
    """Repository for managing variant history audit logs."""

    def __init__(self, db: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            db: Async database session
        """
        self.db = db

    async def log_creation(
        self,
        variant_id: UUID,
        user_id: str,
        content: str,
        version: int,
        status: VariantStatus,
        metadata: Optional[dict] = None,
    ) -> GuardrailVariantHistory:
        """
        Log variant creation.

        Args:
            variant_id: Variant UUID
            user_id: User ID
            content: Initial content
            version: Initial version
            status: Initial status
            metadata: Optional metadata

        Returns:
            GuardrailVariantHistory: Created history entry
        """
        history = GuardrailVariantHistory(
            variant_id=variant_id,
            user_id=user_id,
            action=HistoryAction.CREATED,
            new_content=content,
            new_version=version,
            new_status=status,
            change_summary="Variant created",
            metadata=metadata,
        )
        self.db.add(history)
        await self.db.commit()
        await self.db.refresh(history)
        return history

    async def log_update(
        self,
        variant_id: UUID,
        user_id: str,
        old_content: str,
        new_content: str,
        old_version: int,
        new_version: int,
        change_summary: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> GuardrailVariantHistory:
        """
        Log variant update.

        Args:
            variant_id: Variant UUID
            user_id: User ID
            old_content: Previous content
            new_content: New content
            old_version: Previous version
            new_version: New version
            change_summary: Summary of changes
            metadata: Optional metadata

        Returns:
            GuardrailVariantHistory: Created history entry
        """
        history = GuardrailVariantHistory(
            variant_id=variant_id,
            user_id=user_id,
            action=HistoryAction.UPDATED,
            old_content=old_content,
            new_content=new_content,
            old_version=old_version,
            new_version=new_version,
            change_summary=change_summary or "Variant updated",
            metadata=metadata,
        )
        self.db.add(history)
        await self.db.commit()
        await self.db.refresh(history)
        return history

    async def log_activation(
        self,
        variant_id: UUID,
        user_id: str,
        activated: bool,
        metadata: Optional[dict] = None,
    ) -> GuardrailVariantHistory:
        """
        Log variant activation/deactivation.

        Args:
            variant_id: Variant UUID
            user_id: User ID
            activated: Whether variant was activated (True) or deactivated (False)
            metadata: Optional metadata

        Returns:
            GuardrailVariantHistory: Created history entry
        """
        action = HistoryAction.ACTIVATED if activated else HistoryAction.DEACTIVATED
        summary = "Variant activated" if activated else "Variant deactivated"

        history = GuardrailVariantHistory(
            variant_id=variant_id,
            user_id=user_id,
            action=action,
            change_summary=summary,
            metadata=metadata,
        )
        self.db.add(history)
        await self.db.commit()
        await self.db.refresh(history)
        return history

    async def log_status_change(
        self,
        variant_id: UUID,
        user_id: str,
        old_status: VariantStatus,
        new_status: VariantStatus,
        metadata: Optional[dict] = None,
    ) -> GuardrailVariantHistory:
        """
        Log variant status change.

        Args:
            variant_id: Variant UUID
            user_id: User ID
            old_status: Previous status
            new_status: New status
            metadata: Optional metadata

        Returns:
            GuardrailVariantHistory: Created history entry
        """
        action = HistoryAction.ARCHIVED if new_status == VariantStatus.ARCHIVED else HistoryAction.STATUS_CHANGED
        summary = f"Status changed from {old_status.value} to {new_status.value}"

        history = GuardrailVariantHistory(
            variant_id=variant_id,
            user_id=user_id,
            action=action,
            old_status=old_status,
            new_status=new_status,
            change_summary=summary,
            metadata=metadata,
        )
        self.db.add(history)
        await self.db.commit()
        await self.db.refresh(history)
        return history

    async def get_by_variant(
        self,
        variant_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[GuardrailVariantHistory], int]:
        """
        Get history entries for a variant with pagination.

        Args:
            variant_id: Variant UUID
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            tuple: (list of history entries, total count)
        """
        # Build query
        query = select(GuardrailVariantHistory).where(
            GuardrailVariantHistory.variant_id == variant_id
        )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Apply pagination and ordering
        query = (
            query.order_by(GuardrailVariantHistory.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def get_latest_by_variant(
        self, variant_id: UUID, limit: int = 10
    ) -> List[GuardrailVariantHistory]:
        """
        Get latest history entries for a variant.

        Args:
            variant_id: Variant UUID
            limit: Maximum number of entries to return

        Returns:
            List[GuardrailVariantHistory]: Latest history entries
        """
        result = await self.db.execute(
            select(GuardrailVariantHistory)
            .where(GuardrailVariantHistory.variant_id == variant_id)
            .order_by(GuardrailVariantHistory.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[GuardrailVariantHistory], int]:
        """
        Get all history entries for a user with pagination.

        Args:
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            tuple: (list of history entries, total count)
        """
        # Build query
        query = select(GuardrailVariantHistory).where(
            GuardrailVariantHistory.user_id == user_id
        )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Apply pagination and ordering
        query = (
            query.order_by(GuardrailVariantHistory.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def count_by_variant(self, variant_id: UUID) -> int:
        """
        Count history entries for a variant.

        Args:
            variant_id: Variant UUID

        Returns:
            int: Number of history entries
        """
        result = await self.db.execute(
            select(func.count()).where(GuardrailVariantHistory.variant_id == variant_id)
        )
        return result.scalar_one()

    async def get_by_id(self, history_id: UUID) -> Optional[GuardrailVariantHistory]:
        """
        Get a history entry by ID.

        Args:
            history_id: History entry UUID

        Returns:
            Optional[GuardrailVariantHistory]: History entry if found, None otherwise
        """
        result = await self.db.execute(
            select(GuardrailVariantHistory).where(GuardrailVariantHistory.id == history_id)
        )
        return result.scalar_one_or_none()

```
==================================================

### File: app/repositories/variant_repository.py
```
"""
Repository for GuardrailVariant CRUD operations.
Handles database access for guardrail variants with versioning.
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import GuardrailVariant, VariantStatus


class VariantRepository:
    """Repository for managing guardrail variants in the database."""

    def __init__(self, db: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            db: Async database session
        """
        self.db = db

    async def create(
        self,
        generation_id: UUID,
        user_id: str,
        name: str,
        guardrail_content: str,
        description: Optional[str] = None,
        status: VariantStatus = VariantStatus.DRAFT,
        tags: Optional[List[str]] = None,
        metadata: Optional[dict] = None,
    ) -> GuardrailVariant:
        """
        Create a new guardrail variant.

        Args:
            generation_id: ID of the parent generation
            user_id: ID of the user creating the variant
            name: Variant name
            guardrail_content: Guardrail content
            description: Optional description
            status: Initial status
            tags: Optional tags
            metadata: Additional metadata

        Returns:
            GuardrailVariant: Created variant instance
        """
        variant = GuardrailVariant(
            generation_id=generation_id,
            user_id=user_id,
            name=name,
            description=description,
            guardrail_content=guardrail_content,
            version=1,
            is_active=True,
            status=status,
            tags=tags,
            metadata=metadata,
        )
        self.db.add(variant)
        await self.db.commit()
        await self.db.refresh(variant)
        return variant

    async def get_by_id(self, variant_id: UUID) -> Optional[GuardrailVariant]:
        """
        Get a variant by ID.

        Args:
            variant_id: Variant UUID

        Returns:
            Optional[GuardrailVariant]: Variant if found, None otherwise
        """
        result = await self.db.execute(
            select(GuardrailVariant).where(GuardrailVariant.id == variant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_user(
        self, variant_id: UUID, user_id: str
    ) -> Optional[GuardrailVariant]:
        """
        Get a variant by ID and user (for access control).

        Args:
            variant_id: Variant UUID
            user_id: User ID

        Returns:
            Optional[GuardrailVariant]: Variant if found and belongs to user, None otherwise
        """
        result = await self.db.execute(
            select(GuardrailVariant).where(
                GuardrailVariant.id == variant_id,
                GuardrailVariant.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        generation_id: Optional[UUID] = None,
        status: Optional[VariantStatus] = None,
        is_active: Optional[bool] = None,
        tags: Optional[List[str]] = None,
    ) -> tuple[List[GuardrailVariant], int]:
        """
        List variants for a user with pagination and filtering.

        Args:
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Number of items per page
            generation_id: Optional generation ID filter
            status: Optional status filter
            is_active: Optional active state filter
            tags: Optional tags filter (matches any tag)

        Returns:
            tuple: (list of variants, total count)
        """
        # Build query
        query = select(GuardrailVariant).where(GuardrailVariant.user_id == user_id)

        if generation_id:
            query = query.where(GuardrailVariant.generation_id == generation_id)

        if status:
            query = query.where(GuardrailVariant.status == status)

        if is_active is not None:
            query = query.where(GuardrailVariant.is_active == is_active)

        if tags:
            # Match any of the provided tags (JSON array overlap)
            tag_conditions = [
                GuardrailVariant.tags.contains([tag]) for tag in tags
            ]
            query = query.where(or_(*tag_conditions))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Apply pagination and ordering
        query = (
            query.order_by(GuardrailVariant.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update(
        self,
        variant: GuardrailVariant,
        name: Optional[str] = None,
        description: Optional[str] = None,
        guardrail_content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[dict] = None,
        increment_version: bool = True,
    ) -> GuardrailVariant:
        """
        Update a variant.

        Args:
            variant: Variant to update
            name: New name
            description: New description
            guardrail_content: New content
            tags: New tags
            metadata: New metadata
            increment_version: Whether to increment version number

        Returns:
            GuardrailVariant: Updated variant
        """
        if name is not None:
            variant.name = name

        if description is not None:
            variant.description = description

        if guardrail_content is not None:
            variant.guardrail_content = guardrail_content

        if tags is not None:
            variant.tags = tags

        if metadata is not None:
            variant.metadata = metadata

        if increment_version:
            variant.version += 1

        await self.db.commit()
        await self.db.refresh(variant)
        return variant

    async def set_active(
        self, variant: GuardrailVariant, is_active: bool
    ) -> GuardrailVariant:
        """
        Set the active state of a variant.

        Args:
            variant: Variant to update
            is_active: New active state

        Returns:
            GuardrailVariant: Updated variant
        """
        variant.is_active = is_active
        await self.db.commit()
        await self.db.refresh(variant)
        return variant

    async def set_status(
        self, variant: GuardrailVariant, status: VariantStatus
    ) -> GuardrailVariant:
        """
        Set the status of a variant.

        Args:
            variant: Variant to update
            status: New status

        Returns:
            GuardrailVariant: Updated variant
        """
        variant.status = status
        await self.db.commit()
        await self.db.refresh(variant)
        return variant

    async def delete(self, variant_id: UUID) -> bool:
        """
        Delete a variant.

        Args:
            variant_id: Variant UUID

        Returns:
            bool: True if deleted, False if not found
        """
        variant = await self.get_by_id(variant_id)
        if not variant:
            return False

        await self.db.delete(variant)
        await self.db.commit()
        return True

    async def delete_by_user(self, variant_id: UUID, user_id: str) -> bool:
        """
        Delete a variant (user-scoped for access control).

        Args:
            variant_id: Variant UUID
            user_id: User ID

        Returns:
            bool: True if deleted, False if not found or access denied
        """
        variant = await self.get_by_id_and_user(variant_id, user_id)
        if not variant:
            return False

        await self.db.delete(variant)
        await self.db.commit()
        return True

    async def get_active_variant_for_generation(
        self, generation_id: UUID, user_id: str
    ) -> Optional[GuardrailVariant]:
        """
        Get the active variant for a generation.

        Args:
            generation_id: Generation UUID
            user_id: User ID

        Returns:
            Optional[GuardrailVariant]: Active variant if found, None otherwise
        """
        result = await self.db.execute(
            select(GuardrailVariant)
            .where(
                GuardrailVariant.generation_id == generation_id,
                GuardrailVariant.user_id == user_id,
                GuardrailVariant.is_active == True,
                GuardrailVariant.status == VariantStatus.ACTIVE,
            )
            .order_by(GuardrailVariant.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def count_by_generation(self, generation_id: UUID) -> int:
        """
        Count variants for a generation.

        Args:
            generation_id: Generation UUID

        Returns:
            int: Number of variants
        """
        result = await self.db.execute(
            select(func.count()).where(GuardrailVariant.generation_id == generation_id)
        )
        return result.scalar_one()

    async def list_by_generation(
        self, generation_id: UUID, user_id: str
    ) -> List[GuardrailVariant]:
        """
        List all variants for a generation.

        Args:
            generation_id: Generation UUID
            user_id: User ID

        Returns:
            List[GuardrailVariant]: List of variants
        """
        result = await self.db.execute(
            select(GuardrailVariant)
            .where(
                GuardrailVariant.generation_id == generation_id,
                GuardrailVariant.user_id == user_id,
            )
            .order_by(GuardrailVariant.version.desc())
        )
        return list(result.scalars().all())

```
==================================================

### File: app/services/__init__.py
```

```
==================================================

### File: app/services/guardrail_service.py
```
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

```
==================================================

### File: app/services/llm_service.py
```
"""LLM service - handles LLM provider integrations."""

from enum import Enum
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod

from app.config import get_settings


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"


class LLMError(Exception):
    """Base exception for LLM errors."""
    pass


class LLMProviderNotConfiguredError(LLMError):
    """Raised when LLM provider is not configured."""

    def __init__(self, provider: str):
        self.provider = provider
        super().__init__(f"LLM provider '{provider}' is not configured")


class LLMAPIError(LLMError):
    """Raised when LLM API call fails."""

    def __init__(self, provider: str, message: str):
        self.provider = provider
        super().__init__(f"LLM API error ({provider}): {message}")


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        """Generate text from prompt."""
        pass

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        """Chat completion with messages."""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI API client."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        """Generate text using OpenAI."""
        try:
            response = await self.client.chat.completions.create(
                model=model or "gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise LLMAPIError("openai", str(e))

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        """Chat completion using OpenAI."""
        try:
            response = await self.client.chat.completions.create(
                model=model or "gpt-4o-mini",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise LLMAPIError("openai", str(e))


class AnthropicClient(BaseLLMClient):
    """Anthropic API client."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        """Generate text using Anthropic."""
        try:
            response = await self.client.messages.create(
                model=model or "claude-3-haiku-20240307",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
                **kwargs,
            )
            return response.content[0].text if response.content else ""
        except Exception as e:
            raise LLMAPIError("anthropic", str(e))

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        """Chat completion using Anthropic."""
        try:
            # Convert messages to Anthropic format
            anthropic_messages = []
            system_message = None

            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    anthropic_messages.append({
                        "role": msg["role"],
                        "content": msg["content"],
                    })

            create_kwargs = {
                "model": model or "claude-3-haiku-20240307",
                "max_tokens": max_tokens,
                "messages": anthropic_messages,
                **kwargs,
            }

            if system_message:
                create_kwargs["system"] = system_message

            response = await self.client.messages.create(**create_kwargs)
            return response.content[0].text if response.content else ""
        except Exception as e:
            raise LLMAPIError("anthropic", str(e))


class GroqClient(BaseLLMClient):
    """Groq API client - uses OpenAI-compatible API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url="https://api.groq.com/openai/v1",
            )
        return self._client

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        """Generate text using Groq."""
        try:
            response = await self.client.chat.completions.create(
                model=model or "llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise LLMAPIError("groq", str(e))

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        """Chat completion using Groq."""
        try:
            response = await self.client.chat.completions.create(
                model=model or "llama-3.3-70b-versatile",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise LLMAPIError("groq", str(e))


class LLMService:
    """Service for LLM operations.

    Supports multiple providers (OpenAI, Anthropic, Groq) with fallback.
    """

    def __init__(self):
        self.settings = get_settings()
        self._clients: Dict[LLMProvider, BaseLLMClient] = {}

    def _get_client(self, provider: LLMProvider) -> BaseLLMClient:
        """Get or create client for provider."""
        if provider in self._clients:
            return self._clients[provider]

        if provider == LLMProvider.OPENAI:
            if not self.settings.openai_api_key:
                raise LLMProviderNotConfiguredError("openai")
            self._clients[provider] = OpenAIClient(self.settings.openai_api_key)
        elif provider == LLMProvider.ANTHROPIC:
            if not self.settings.anthropic_api_key:
                raise LLMProviderNotConfiguredError("anthropic")
            self._clients[provider] = AnthropicClient(self.settings.anthropic_api_key)
        elif provider == LLMProvider.GROQ:
            if not self.settings.groq_api_key:
                raise LLMProviderNotConfiguredError("groq")
            self._clients[provider] = GroqClient(self.settings.groq_api_key)
        else:
            raise LLMProviderNotConfiguredError(provider)

        return self._clients[provider]

    def _get_default_provider(self) -> LLMProvider:
        """Get default provider from settings."""
        provider_str = self.settings.default_llm_provider.lower()
        if provider_str == "anthropic":
            return LLMProvider.ANTHROPIC
        elif provider_str == "groq":
            return LLMProvider.GROQ
        return LLMProvider.OPENAI

    async def generate(
        self,
        prompt: str,
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        """Generate text using specified or default provider.

        Args:
            prompt: The prompt text
            provider: LLM provider to use (defaults to settings)
            model: Model to use (defaults to provider's default)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text

        Raises:
            LLMProviderNotConfiguredError: If provider not configured
            LLMAPIError: If API call fails
        """
        provider = provider or self._get_default_provider()
        client = self._get_client(provider)
        return await client.generate(
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    async def chat(
        self,
        messages: List[Dict[str, str]],
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        """Chat completion using specified or default provider.

        Args:
            messages: List of message dicts with 'role' and 'content'
            provider: LLM provider to use (defaults to settings)
            model: Model to use (defaults to provider's default)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated response text

        Raises:
            LLMProviderNotConfiguredError: If provider not configured
            LLMAPIError: If API call fails
        """
        provider = provider or self._get_default_provider()
        client = self._get_client(provider)
        return await client.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    def is_provider_configured(self, provider: LLMProvider) -> bool:
        """Check if a provider is configured."""
        if provider == LLMProvider.OPENAI:
            return bool(self.settings.openai_api_key)
        elif provider == LLMProvider.ANTHROPIC:
            return bool(self.settings.anthropic_api_key)
        elif provider == LLMProvider.GROQ:
            return bool(self.settings.groq_api_key)
        return False

    def get_configured_providers(self) -> List[LLMProvider]:
        """Get list of configured providers."""
        return [p for p in LLMProvider if self.is_provider_configured(p)]

```
==================================================

### File: app/services/template_service.py
```
"""
Template Service - manages guardrail template operations.
Handles template retrieval, validation, and preview.
"""

from typing import Dict, List, Any, Optional

from app.templates.registry import (
    get_template,
    list_templates,
    get_template_keys,
    validate_template_key,
    TemplateNotFoundError,
)
from app.templates.base import GuardrailStrategy


class TemplateService:
    """
    Service for guardrail template operations.

    This service reads templates from code (registry) and does NOT
    interact with the database. It's stateless and provides template
    information and generation capabilities.
    """

    def list_all_templates(self) -> List[Dict[str, Any]]:
        """
        Get all available guardrail templates.

        Returns:
            List[dict]: List of template metadata
        """
        return list_templates()

    def get_template_keys(self) -> List[str]:
        """
        Get all available template keys.

        Returns:
            List[str]: List of template keys
        """
        return get_template_keys()

    def get_template_info(self, template_key: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific template.

        Args:
            template_key: Template key

        Returns:
            dict: Template information including parameters

        Raises:
            TemplateNotFoundError: If template doesn't exist
        """
        template = get_template(template_key)
        info = template.to_dict()
        info["parameters"] = template.get_parameters()
        return info

    def validate_template_key(self, template_key: str) -> bool:
        """
        Validate that a template key exists.

        Args:
            template_key: Template key to validate

        Returns:
            bool: True if valid, False otherwise
        """
        return validate_template_key(template_key)

    def build_guardrail(
        self,
        template_key: str,
        user_context: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build a guardrail using the specified template.

        Args:
            template_key: Template to use
            user_context: User-provided context
            parameters: Template-specific parameters

        Returns:
            str: Generated guardrail content

        Raises:
            TemplateNotFoundError: If template doesn't exist
        """
        template = get_template(template_key)
        params = parameters or {}
        return template.build_guardrail(user_context, **params)

    def preview_guardrail(
        self,
        template_key: str,
        user_context: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Preview a guardrail without saving to database.

        Args:
            template_key: Template to use
            user_context: User-provided context
            parameters: Template-specific parameters

        Returns:
            dict: Preview information including generated guardrail

        Raises:
            TemplateNotFoundError: If template doesn't exist
        """
        guardrail_content = self.build_guardrail(template_key, user_context, parameters)
        template = get_template(template_key)

        return {
            "template_key": template_key,
            "template_name": template.name.replace("_", " ").title(),
            "generated_guardrail": guardrail_content,
            "parameters": parameters,
        }

    def get_template_count(self) -> int:
        """
        Get the total number of available templates.

        Returns:
            int: Number of templates
        """
        return len(get_template_keys())

```
==================================================

### File: app/services/variant_service.py
```
"""
Variant Service - manages guardrail variant operations.
Handles variant creation, updates, versioning, and history tracking.
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import GuardrailVariant, VariantStatus
from app.models.schemas import (
    CreateVariantRequest,
    UpdateVariantRequest,
    GuardrailVariantResponse,
    SetVariantStatusRequest,
    SetVariantActiveRequest,
    GuardrailVariantHistoryResponse,
)
from app.repositories.variant_repository import VariantRepository
from app.repositories.generation_repository import GenerationRepository
from app.repositories.history_repository import HistoryRepository


class VariantNotFoundError(Exception):
    """Raised when a variant is not found."""

    def __init__(self, variant_id: UUID):
        super().__init__(f"Variant '{variant_id}' not found")


class GenerationNotFoundError(Exception):
    """Raised when a generation is not found."""

    def __init__(self, generation_id: UUID):
        super().__init__(f"Generation '{generation_id}' not found")


class VariantService:
    """
    Service for guardrail variant management.

    Handles variant CRUD operations, versioning, and history tracking.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize service with database session.

        Args:
            db: Async database session
        """
        self.db = db
        self.variant_repo = VariantRepository(db)
        self.generation_repo = GenerationRepository(db)
        self.history_repo = HistoryRepository(db)

    async def create_variant(
        self, request: CreateVariantRequest
    ) -> GuardrailVariantResponse:
        """
        Create a new variant from a generation.

        Args:
            request: Variant creation request

        Returns:
            GuardrailVariantResponse: Created variant

        Raises:
            GenerationNotFoundError: If generation doesn't exist or access denied
        """
        # Verify generation exists and belongs to user
        generation = await self.generation_repo.get_by_id_and_user(
            UUID(request.generation_id), request.user_id
        )
        if not generation:
            raise GenerationNotFoundError(UUID(request.generation_id))

        # Use generation's content if custom content not provided
        guardrail_content = request.guardrail_content or generation.generated_guardrail

        # Create variant
        variant = await self.variant_repo.create(
            generation_id=UUID(request.generation_id),
            user_id=request.user_id,
            name=request.name,
            description=request.description,
            guardrail_content=guardrail_content,
            status=request.status or VariantStatus.DRAFT,
            tags=request.tags,
            metadata=request.metadata,
        )

        # Log creation in history
        await self.history_repo.log_creation(
            variant_id=variant.id,
            user_id=request.user_id,
            content=guardrail_content,
            version=1,
            status=variant.status,
            metadata=request.metadata,
        )

        return self._to_response(variant)

    async def get_variant(
        self, variant_id: UUID, user_id: str
    ) -> Optional[GuardrailVariantResponse]:
        """
        Get a variant by ID (user-scoped).

        Args:
            variant_id: Variant UUID
            user_id: User ID for access control

        Returns:
            Optional[GuardrailVariantResponse]: Variant if found, None otherwise
        """
        variant = await self.variant_repo.get_by_id_and_user(variant_id, user_id)
        if not variant:
            return None
        return self._to_response(variant)

    async def list_variants(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        generation_id: Optional[UUID] = None,
        status: Optional[VariantStatus] = None,
        is_active: Optional[bool] = None,
        tags: Optional[List[str]] = None,
    ) -> tuple[List[GuardrailVariantResponse], int]:
        """
        List variants for a user with pagination and filters.

        Args:
            user_id: User ID
            page: Page number
            page_size: Items per page
            generation_id: Optional generation filter
            status: Optional status filter
            is_active: Optional active state filter
            tags: Optional tags filter

        Returns:
            tuple: (list of variants, total count)
        """
        variants, total = await self.variant_repo.list_by_user(
            user_id=user_id,
            page=page,
            page_size=page_size,
            generation_id=generation_id,
            status=status,
            is_active=is_active,
            tags=tags,
        )
        responses = [self._to_response(var) for var in variants]
        return responses, total

    async def create_new_version(
        self, source_variant_id: UUID, request: UpdateVariantRequest
    ) -> GuardrailVariantResponse:
        """
        Create a new version of a variant (insert-only, no update).

        This follows the versioning principle: never update existing records,
        always create new versions. The source variant remains unchanged.

        Args:
            source_variant_id: Source variant UUID to create new version from
            request: New version request with updated content

        Returns:
            GuardrailVariantResponse: Newly created variant with incremented version

        Raises:
            VariantNotFoundError: If source variant doesn't exist or access denied
        """
        # Get source variant
        source_variant = await self.variant_repo.get_by_id_and_user(source_variant_id, request.user_id)
        if not source_variant:
            raise VariantNotFoundError(source_variant_id)

        # Determine new version number
        new_version = source_variant.version + 1

        # Use provided values or keep from source variant
        new_name = request.name if request.name else source_variant.name
        new_description = request.description if request.description is not None else source_variant.description
        new_content = request.guardrail_content if request.guardrail_content else source_variant.guardrail_content
        new_tags = request.tags if request.tags is not None else source_variant.tags
        new_metadata = request.metadata if request.metadata is not None else source_variant.metadata

        # Create new variant (new record, not update)
        new_variant = await self.variant_repo.create(
            generation_id=source_variant.generation_id,
            user_id=request.user_id,
            name=new_name,
            description=new_description,
            guardrail_content=new_content,
            status=source_variant.status,  # Keep same status
            tags=new_tags,
            metadata=new_metadata,
        )

        # Manually set version (override default version=1)
        new_variant.version = new_version
        await self.db.commit()
        await self.db.refresh(new_variant)

        # Log creation of new version in history
        await self.history_repo.log_update(
            variant_id=new_variant.id,
            user_id=request.user_id,
            old_content=source_variant.guardrail_content,
            new_content=new_content,
            old_version=source_variant.version,
            new_version=new_version,
            change_summary=request.change_summary or f"Created new version from v{source_variant.version}",
            metadata={"source_variant_id": str(source_variant_id)},
        )

        return self._to_response(new_variant)

    async def set_variant_active(
        self, variant_id: UUID, request: SetVariantActiveRequest
    ) -> GuardrailVariantResponse:
        """
        Activate or deactivate a variant.

        Args:
            variant_id: Variant UUID
            request: Activation request

        Returns:
            GuardrailVariantResponse: Updated variant

        Raises:
            VariantNotFoundError: If variant doesn't exist or access denied
        """
        # Get variant
        variant = await self.variant_repo.get_by_id_and_user(variant_id, request.user_id)
        if not variant:
            raise VariantNotFoundError(variant_id)

        # Update active state
        variant = await self.variant_repo.set_active(variant, request.is_active)

        # Log activation/deactivation
        await self.history_repo.log_activation(
            variant_id=variant.id,
            user_id=request.user_id,
            activated=request.is_active,
        )

        return self._to_response(variant)

    async def set_variant_status(
        self, variant_id: UUID, request: SetVariantStatusRequest
    ) -> GuardrailVariantResponse:
        """
        Change variant status.

        Args:
            variant_id: Variant UUID
            request: Status change request

        Returns:
            GuardrailVariantResponse: Updated variant

        Raises:
            VariantNotFoundError: If variant doesn't exist or access denied
        """
        # Get variant
        variant = await self.variant_repo.get_by_id_and_user(variant_id, request.user_id)
        if not variant:
            raise VariantNotFoundError(variant_id)

        # Store old status for history
        old_status = variant.status

        # Update status
        variant = await self.variant_repo.set_status(variant, request.status)

        # Log status change
        await self.history_repo.log_status_change(
            variant_id=variant.id,
            user_id=request.user_id,
            old_status=old_status,
            new_status=request.status,
        )

        return self._to_response(variant)

    async def delete_variant(self, variant_id: UUID, user_id: str) -> bool:
        """
        Delete a variant (user-scoped).

        Args:
            variant_id: Variant UUID
            user_id: User ID for access control

        Returns:
            bool: True if deleted, False if not found
        """
        return await self.variant_repo.delete_by_user(variant_id, user_id)

    async def get_variant_history(
        self, variant_id: UUID, user_id: str, page: int = 1, page_size: int = 20
    ) -> tuple[List[GuardrailVariantHistoryResponse], int]:
        """
        Get history for a variant.

        Args:
            variant_id: Variant UUID
            user_id: User ID for access control
            page: Page number
            page_size: Items per page

        Returns:
            tuple: (list of history entries, total count)

        Raises:
            VariantNotFoundError: If variant doesn't exist or access denied
        """
        # Verify variant exists and belongs to user
        variant = await self.variant_repo.get_by_id_and_user(variant_id, user_id)
        if not variant:
            raise VariantNotFoundError(variant_id)

        # Get history
        history_entries, total = await self.history_repo.get_by_variant(
            variant_id=variant_id,
            page=page,
            page_size=page_size,
        )

        responses = [self._history_to_response(entry) for entry in history_entries]
        return responses, total

    async def list_variants_by_generation(
        self, generation_id: UUID, user_id: str
    ) -> List[GuardrailVariantResponse]:
        """
        List all variants for a specific generation.

        Args:
            generation_id: Generation UUID
            user_id: User ID for access control

        Returns:
            List[GuardrailVariantResponse]: List of variants

        Raises:
            GenerationNotFoundError: If generation doesn't exist or access denied
        """
        # Verify generation exists and belongs to user
        generation = await self.generation_repo.get_by_id_and_user(generation_id, user_id)
        if not generation:
            raise GenerationNotFoundError(generation_id)

        # Get variants
        variants = await self.variant_repo.list_by_generation(generation_id, user_id)
        return [self._to_response(var) for var in variants]

    def _to_response(self, variant: GuardrailVariant) -> GuardrailVariantResponse:
        """
        Convert database model to response schema.

        Args:
            variant: Database model

        Returns:
            GuardrailVariantResponse: Response schema
        """
        return GuardrailVariantResponse(
            id=str(variant.id),
            generation_id=str(variant.generation_id),
            user_id=variant.user_id,
            name=variant.name,
            description=variant.description,
            guardrail_content=variant.guardrail_content,
            version=variant.version,
            is_active=variant.is_active,
            status=variant.status,
            tags=variant.tags,
            metadata=variant.metadata,
            created_at=variant.created_at,
            updated_at=variant.updated_at,
        )

    def _history_to_response(self, history) -> GuardrailVariantHistoryResponse:
        """
        Convert history model to response schema.

        Args:
            history: Database model

        Returns:
            GuardrailVariantHistoryResponse: Response schema
        """
        return GuardrailVariantHistoryResponse(
            id=str(history.id),
            variant_id=str(history.variant_id),
            user_id=history.user_id,
            action=history.action,
            old_content=history.old_content,
            new_content=history.new_content,
            old_version=history.old_version,
            new_version=history.new_version,
            old_status=history.old_status,
            new_status=history.new_status,
            change_summary=history.change_summary,
            metadata=history.metadata,
            created_at=history.created_at,
        )

```
==================================================

### File: app/templates/__init__.py
```

```
==================================================

### File: app/templates/base.py
```
"""
Base class for guardrail template strategies.
All guardrail templates must inherit from GuardrailStrategy.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class GuardrailStrategy(ABC):
    """
    Abstract base class for guardrail generation strategies.

    Each strategy represents a different type of guardrail that can be
    applied to LLM interactions to ensure safety, compliance, or quality.
    """

    name: str
    description: str

    @abstractmethod
    def build_guardrail(self, user_context: str, **kwargs) -> str:
        """
        Build the guardrail prompt/rules based on user context.

        Args:
            user_context: User-provided context or requirements for the guardrail
            **kwargs: Additional parameters specific to the guardrail type

        Returns:
            str: The generated guardrail prompt/rules
        """
        pass

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert strategy to dictionary representation.

        Returns:
            dict: Strategy metadata including key, name, and description
        """
        return {
            "key": self.name,
            "name": self.name.replace("_", " ").title(),
            "description": self.description,
        }

    def get_parameters(self) -> Dict[str, Any]:
        """
        Get the parameters that this guardrail accepts.

        Returns:
            dict: Parameter definitions with types and descriptions
        """
        return {}

```
==================================================

### File: app/templates/compliance.py
```
"""
Compliance Guardrail Strategy.
Ensures adherence to regulatory and legal requirements.
"""

from app.templates.base import GuardrailStrategy


class ComplianceStrategy(GuardrailStrategy):
    """
    Guardrail to ensure regulatory and legal compliance.
    """

    name = "compliance"
    description = "Ensures adherence to regulatory and legal requirements (GDPR, HIPAA, etc.)"

    def build_guardrail(self, user_context: str, **kwargs) -> str:
        """
        Build compliance guardrail.

        Args:
            user_context: Description of regulatory context
            **kwargs: Additional parameters (regulations, jurisdiction)
        """
        regulations = kwargs.get("regulations", ["GDPR"])
        jurisdiction = kwargs.get("jurisdiction", "EU")
        industry = kwargs.get("industry", "general")

        regulations_list = ", ".join(regulations)

        return f"""# Compliance Guardrail

## Context
{user_context}

## Applicable Regulations: {regulations_list}
## Jurisdiction: {jurisdiction}
## Industry: {industry.title()}

## Regulatory Compliance Requirements

{self._get_regulation_requirements(regulations)}

## General Compliance Principles

### Data Handling
1. **Data Minimization**: Only collect and process necessary data
2. **Purpose Limitation**: Use data only for stated purposes
3. **Storage Limitation**: Don't retain data longer than necessary
4. **Accuracy**: Ensure data is accurate and up-to-date
5. **Security**: Implement appropriate security measures

### User Rights
1. **Right to Information**: Clear communication about data use
2. **Right to Access**: Users can request their data
3. **Right to Rectification**: Users can correct their data
4. **Right to Erasure**: Users can request data deletion
5. **Right to Portability**: Users can transfer their data
6. **Right to Object**: Users can object to processing

### Consent Management
- Obtain explicit consent before data processing
- Make consent withdrawal as easy as giving it
- Keep records of consent
- Don't use pre-ticked boxes
- Separate consent for different purposes

### Required Disclosures
Always inform users about:
- What data is collected
- Why it's collected
- How it's used
- Who has access to it
- How long it's retained
- Their rights regarding the data

## Industry-Specific Requirements

{self._get_industry_requirements(industry)}

## Prohibited Activities

### Never Do:
- Process data without legal basis
- Share data with unauthorized parties
- Retain data beyond necessary period
- Use data for undisclosed purposes
- Make automated decisions without human review (when required)
- Transfer data outside approved jurisdictions without safeguards
- Ignore data subject requests
- Fail to report breaches within required timeframe

### Always Do:
- Document legal basis for processing
- Implement privacy by design
- Conduct data protection impact assessments (when required)
- Maintain processing records
- Have data breach response procedures
- Honor user rights requests promptly
- Provide clear privacy notices
- Implement appropriate security measures

## Response Guidelines

### When Handling Personal Data:
1. Verify legal basis exists
2. Apply data minimization
3. Ensure security measures
4. Document the processing
5. Respect user rights

### When Responding to Users:
1. Provide clear, plain language explanations
2. Include required disclosures
3. Explain their rights
4. Offer opt-out mechanisms
5. Provide contact information for questions

### Red Flags - Stop Immediately:
- Request to process sensitive data without clear authorization
- Instruction to bypass consent requirements
- Request to share data with unauthorized parties
- Instruction to retain data indefinitely
- Request to make high-impact automated decisions without review
- Attempt to transfer data to non-compliant jurisdiction

## Breach Response Protocol

If a potential data breach is detected:
1. Immediately stop the activity
2. Escalate to appropriate personnel
3. Document the incident
4. Follow breach notification procedures
5. Implement remediation measures

## Disclaimer Requirements

Include appropriate disclaimers:
- "This is not legal advice. Consult with qualified professionals."
- "Compliance requirements vary by jurisdiction."
- "This information is current as of [date]."
- "Individual circumstances may require additional measures."

## Audit Trail

Maintain records of:
- What data was processed
- When it was processed
- Why it was processed
- Who authorized the processing
- What security measures were applied
"""

    def _get_regulation_requirements(self, regulations: list) -> str:
        """Get specific requirements for each regulation."""
        requirements = {
            "GDPR": """### GDPR (General Data Protection Regulation)
- **Scope**: EU residents' personal data
- **Key Requirements**:
  - Lawful basis for processing (consent, contract, legal obligation, etc.)
  - Data protection principles (lawfulness, fairness, transparency)
  - User rights (access, rectification, erasure, portability, objection)
  - Data breach notification (72 hours to supervisory authority)
  - Privacy by design and default
  - Data Protection Impact Assessments for high-risk processing
  - DPO appointment (when required)
- **Penalties**: Up to €20M or 4% of global turnover""",
            "HIPAA": """### HIPAA (Health Insurance Portability and Accountability Act)
- **Scope**: Protected Health Information (PHI) in the US
- **Key Requirements**:
  - Privacy Rule: Limits on PHI use and disclosure
  - Security Rule: Administrative, physical, technical safeguards
  - Breach Notification Rule: Notify affected individuals and HHS
  - Minimum necessary standard: Only access/use PHI needed
  - Business Associate Agreements required
  - Patient rights: Access, amendment, accounting of disclosures
- **Penalties**: Up to $1.5M per violation category per year""",
            "CCPA": """### CCPA (California Consumer Privacy Act)
- **Scope**: California residents' personal information
- **Key Requirements**:
  - Consumer rights: Know, delete, opt-out, non-discrimination
  - Notice at collection required
  - Privacy policy disclosure requirements
  - Opt-out of sale of personal information
  - Opt-in for minors under 16
  - Reasonable security measures
  - 30-day cure period for violations
- **Penalties**: Up to $7,500 per intentional violation""",
            "PCI-DSS": """### PCI-DSS (Payment Card Industry Data Security Standard)
- **Scope**: Payment card data
- **Key Requirements**:
  - Build and maintain secure network
  - Protect cardholder data (encryption)
  - Maintain vulnerability management program
  - Implement strong access control measures
  - Regularly monitor and test networks
  - Maintain information security policy
  - Never store sensitive authentication data after authorization
- **Penalties**: Fines from payment brands, potential card processing restrictions""",
            "SOC2": """### SOC 2 (Service Organization Control 2)
- **Scope**: Service providers handling customer data
- **Key Requirements**:
  - Security: Protection against unauthorized access
  - Availability: System available for operation and use
  - Processing Integrity: System processing is complete, valid, accurate, timely
  - Confidentiality: Confidential information protected
  - Privacy: Personal information collected, used, retained, disclosed per commitments
- **Validation**: Independent auditor assessment""",
        }

        result = []
        for reg in regulations:
            if reg in requirements:
                result.append(requirements[reg])
            else:
                result.append(f"### {reg}\n- Refer to specific {reg} documentation for requirements")

        return "\n\n".join(result)

    def _get_industry_requirements(self, industry: str) -> str:
        """Get industry-specific compliance requirements."""
        requirements = {
            "healthcare": """### Healthcare Industry
- Comply with HIPAA for PHI
- Implement minimum necessary access
- Maintain audit logs for PHI access
- Encrypt PHI in transit and at rest
- Business Associate Agreements required
- Patient consent for specific uses
- Breach notification within 60 days""",
            "finance": """### Financial Services
- Comply with GLBA, PCI-DSS, SOX (as applicable)
- Implement strong authentication
- Encrypt financial data
- Maintain transaction audit trails
- Privacy notices required
- Opt-out rights for information sharing
- Incident response and reporting procedures""",
            "education": """### Education Sector
- Comply with FERPA for student records
- Parental consent for children under 13 (COPPA)
- Limit access to educational records
- Allow parents to review and correct records
- Obtain consent before disclosure
- Maintain security of educational records""",
            "retail": """### Retail Industry
- Comply with PCI-DSS for payment data
- CCPA/GDPR for customer data (jurisdiction-dependent)
- Clear privacy policies
- Secure customer data
- Opt-out mechanisms for marketing
- Data breach notification procedures""",
            "general": """### General Industry
- Follow applicable data protection laws (GDPR, CCPA, etc.)
- Implement reasonable security measures
- Provide privacy notices
- Honor user rights requests
- Report breaches as required
- Maintain compliance documentation""",
        }
        return requirements.get(industry.lower(), requirements["general"])

    def get_parameters(self):
        return {
            "regulations": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["GDPR", "HIPAA", "CCPA", "PCI-DSS", "SOC2", "FERPA", "COPPA"],
                },
                "default": ["GDPR"],
                "description": "Applicable regulations",
            },
            "jurisdiction": {
                "type": "string",
                "default": "EU",
                "description": "Legal jurisdiction (e.g., EU, US, UK)",
            },
            "industry": {
                "type": "string",
                "enum": ["general", "healthcare", "finance", "education", "retail"],
                "default": "general",
                "description": "Industry sector",
            },
        }

```
==================================================

### File: app/templates/content_safety.py
```
"""
Content Safety Guardrail Strategy.
Prevents harmful, offensive, or inappropriate content.
"""

from app.templates.base import GuardrailStrategy


class ContentSafetyStrategy(GuardrailStrategy):
    """
    Guardrail to ensure content safety and prevent harmful outputs.
    """

    name = "content_safety"
    description = "Prevents harmful, offensive, or inappropriate content in AI responses"

    def build_guardrail(self, user_context: str, **kwargs) -> str:
        """
        Build content safety guardrail.

        Args:
            user_context: Description of the use case or domain
            **kwargs: Additional parameters (safety_level, custom_topics)
        """
        safety_level = kwargs.get("safety_level", "standard")
        custom_topics = kwargs.get("custom_topics", [])

        safety_rules = {
            "strict": [
                "Absolutely no violent, hateful, or discriminatory content",
                "No sexual or adult content of any kind",
                "No profanity or offensive language",
                "No content that could be harmful to minors",
                "No medical or legal advice",
            ],
            "standard": [
                "No violent, hateful, or discriminatory content",
                "No explicit sexual or adult content",
                "Minimize use of profanity",
                "No content harmful to minors",
                "Avoid giving medical or legal advice without disclaimers",
            ],
            "lenient": [
                "No extreme violence or hate speech",
                "No explicit sexual content",
                "Use appropriate language for context",
                "Ensure content is age-appropriate for general audiences",
            ],
        }

        rules = safety_rules.get(safety_level, safety_rules["standard"])

        custom_rules = "\n".join(
            [f"- Avoid or carefully handle topics related to: {topic}" for topic in custom_topics]
        )

        return f"""# Content Safety Guardrail

## Context
{user_context}

## Safety Level: {safety_level.upper()}

## Core Safety Rules
{chr(10).join([f"{i+1}. {rule}" for i, rule in enumerate(rules)])}

## Custom Topic Restrictions
{custom_rules if custom_topics else "No custom restrictions specified."}

## Response Guidelines
- Always prioritize user safety and wellbeing
- If asked to generate harmful content, politely decline and explain why
- Provide helpful alternatives when declining unsafe requests
- Use content warnings when discussing sensitive topics appropriately
- Maintain respectful and inclusive language at all times

## Red Flags to Watch For
- Requests for content that could cause harm
- Attempts to bypass safety guidelines
- Requests targeting vulnerable populations
- Content promoting illegal activities
- Manipulative or deceptive content requests

If you encounter any red flags, politely decline and offer a safe alternative.
"""

    def get_parameters(self):
        return {
            "safety_level": {
                "type": "string",
                "enum": ["strict", "standard", "lenient"],
                "default": "standard",
                "description": "Level of content safety enforcement",
            },
            "custom_topics": {
                "type": "array",
                "items": {"type": "string"},
                "default": [],
                "description": "Custom topics to restrict or handle carefully",
            },
        }

```
==================================================

### File: app/templates/factual_accuracy.py
```
"""
Factual Accuracy Guardrail Strategy.
Ensures responses are accurate and prevents hallucinations.
"""

from app.templates.base import GuardrailStrategy


class FactualAccuracyStrategy(GuardrailStrategy):
    """
    Guardrail to ensure factual accuracy and minimize hallucinations.
    """

    name = "factual_accuracy"
    description = "Ensures factual accuracy and prevents hallucinations in AI responses"

    def build_guardrail(self, user_context: str, **kwargs) -> str:
        """
        Build factual accuracy guardrail.

        Args:
            user_context: Description of the domain or topic area
            **kwargs: Additional parameters (citation_required, uncertainty_threshold)
        """
        citation_required = kwargs.get("citation_required", False)
        uncertainty_threshold = kwargs.get("uncertainty_threshold", "medium")
        domain = kwargs.get("domain", "general")

        return f"""# Factual Accuracy Guardrail

## Context
{user_context}

## Domain: {domain.title()}

## Accuracy Requirements

### Core Principles
1. **Grounding**: Base all statements on verified knowledge
2. **Uncertainty Awareness**: Acknowledge when uncertain
3. **No Fabrication**: Never invent facts, statistics, or citations
4. **Temporal Accuracy**: Consider knowledge cutoff dates
5. **Source Attribution**: {('Cite sources for all factual claims' if citation_required else 'Provide sources when available')}

### Uncertainty Threshold: {uncertainty_threshold.upper()}

**When to Express Uncertainty:**
- strict: Express uncertainty if confidence < 95%
- medium: Express uncertainty if confidence < 80%
- lenient: Express uncertainty if confidence < 60%

### Response Quality Guidelines

1. **Fact Verification**
   - Cross-reference information mentally before stating
   - Distinguish between facts and interpretations
   - Avoid absolute statements when data is ambiguous
   - Use qualifying language for uncertain information

2. **Prohibited Behaviors**
   - Making up statistics or data
   - Inventing scientific studies or research
   - Creating fake citations or references
   - Claiming specific knowledge beyond training data
   - Providing medical/legal advice as definitive fact

3. **Required Behaviors**
   - State "I don't know" when genuinely uncertain
   - Provide confidence qualifiers (likely, possibly, may)
   - Acknowledge knowledge cutoff limitations
   - Suggest verifying critical information
   - Distinguish opinions from facts

4. **Citation Requirements** {'(ENABLED)' if citation_required else '(DISABLED)'}
   {'- Include sources for all factual claims' if citation_required else '- Provide sources when available and helpful'}
   {'- Use format: [Statement] (Source: ...)' if citation_required else '- Suggest where to verify information'}
   - Never fabricate citations
   - Admit when source is not available

### Domain-Specific Considerations

**{domain.title()} Domain Guidelines:**
{self._get_domain_guidelines(domain)}

### Red Flags - Stop and Reconsider
- You're about to state a specific statistic without certainty
- You're tempted to fill gaps with plausible-sounding information
- You can't recall the specific source of information
- The claim seems important but you're not fully confident
- User is asking for medical, legal, or financial advice

### Response Template for Uncertain Information
"While [general information], I should note that [uncertainty qualifier]. For precise information, I recommend [verification method]."

### Examples of Good Practices
✓ "Based on widely reported data, approximately X% of..."
✓ "As of my last update in [date], the consensus was..."
✓ "I don't have specific information about that, but generally..."
✓ "This appears to be the case, though I'd recommend verifying..."

### Examples of Bad Practices
✗ Making up specific percentages or statistics
✗ Inventing study names or researcher quotes
✗ Stating opinions as universal facts
✗ Providing medical diagnoses or legal judgments
"""

    def _get_domain_guidelines(self, domain: str) -> str:
        """Get domain-specific accuracy guidelines."""
        guidelines = {
            "medical": """- Never provide diagnoses
- Always recommend consulting healthcare professionals
- Distinguish between general health information and medical advice
- Be especially cautious with dosages, treatments, or symptoms""",
            "legal": """- Never provide specific legal advice
- Always recommend consulting licensed attorneys
- Distinguish between general legal information and advice
- Be cautious with jurisdiction-specific information""",
            "financial": """- Never provide specific investment advice
- Always recommend consulting financial advisors
- Include standard risk disclaimers
- Distinguish between general education and advice""",
            "scientific": """- Cite peer-reviewed sources when possible
- Acknowledge areas of ongoing research or debate
- Distinguish between established science and emerging theories
- Be clear about levels of scientific consensus""",
            "technical": """- Distinguish between standard practices and opinions
- Acknowledge version-specific or platform-specific information
- Recommend checking official documentation
- Be clear about best practices vs. requirements""",
            "general": """- Apply common-sense fact-checking
- Acknowledge areas outside your expertise
- Provide balanced perspectives when appropriate
- Recommend authoritative sources for verification""",
        }
        return guidelines.get(domain.lower(), guidelines["general"])

    def get_parameters(self):
        return {
            "citation_required": {
                "type": "boolean",
                "default": False,
                "description": "Whether citations are required for factual claims",
            },
            "uncertainty_threshold": {
                "type": "string",
                "enum": ["strict", "medium", "lenient"],
                "default": "medium",
                "description": "When to express uncertainty",
            },
            "domain": {
                "type": "string",
                "enum": ["general", "medical", "legal", "financial", "scientific", "technical"],
                "default": "general",
                "description": "Domain-specific accuracy requirements",
            },
        }

```
==================================================

### File: app/templates/pii_protection.py
```
"""
PII Protection Guardrail Strategy.
Prevents leakage of Personally Identifiable Information.
"""

from app.templates.base import GuardrailStrategy


class PIIProtectionStrategy(GuardrailStrategy):
    """
    Guardrail to protect Personally Identifiable Information (PII).
    """

    name = "pii_protection"
    description = "Prevents exposure or leakage of personally identifiable information"

    def build_guardrail(self, user_context: str, **kwargs) -> str:
        """
        Build PII protection guardrail.

        Args:
            user_context: Description of data types being handled
            **kwargs: Additional parameters (pii_types, redaction_strategy)
        """
        pii_types = kwargs.get(
            "pii_types",
            [
                "names",
                "email_addresses",
                "phone_numbers",
                "addresses",
                "social_security_numbers",
                "credit_card_numbers",
            ],
        )
        redaction_strategy = kwargs.get("redaction_strategy", "mask")

        return f"""# PII Protection Guardrail

## Context
{user_context}

## Protected Information Types
The following types of personally identifiable information (PII) must be protected:
{chr(10).join([f"- {pii_type.replace('_', ' ').title()}" for pii_type in pii_types])}

## Redaction Strategy: {redaction_strategy.upper()}

### Handling Guidelines

1. **Detection**: Actively identify PII in user inputs and generated outputs
2. **Redaction Strategy**: {redaction_strategy}
   - `mask`: Replace PII with masked values (e.g., "***-**-1234")
   - `remove`: Completely remove PII from responses
   - `generalize`: Replace with generic placeholders (e.g., "[NAME]", "[EMAIL]")

3. **Never Include in Responses**:
   - Full names when partial reference suffices
   - Complete email addresses (use [EMAIL] or masked version)
   - Phone numbers (use [PHONE] or masked format)
   - Physical addresses (use city/state only if needed)
   - Government ID numbers (SSN, passport, etc.)
   - Financial account numbers
   - Biometric data
   - Login credentials

4. **Safe Alternatives**:
   - Use anonymous identifiers (User A, Customer 1)
   - Reference roles instead of names (e.g., "the manager")
   - Use generic examples that don't expose real data
   - Aggregate data when possible

## Response Validation Checklist
Before generating any response, verify:
- [ ] No full names are exposed unnecessarily
- [ ] No email addresses are displayed in full
- [ ] No phone numbers are revealed
- [ ] No addresses are included
- [ ] No government IDs or financial account numbers
- [ ] No passwords or credentials
- [ ] PII in examples has been anonymized

## Handling User Requests for PII
- If user asks to include PII: Politely decline and explain privacy concerns
- Offer to use anonymized or masked alternatives
- Suggest using secure channels for sensitive information
- Never generate synthetic PII that could be confused with real data

## Emergency Override
Only include PII if:
1. Explicitly required for the task AND
2. User has confirmed they have authorization AND
3. The context is clearly internal/authorized use

In all cases, add a warning about handling sensitive information responsibly.
"""

    def get_parameters(self):
        return {
            "pii_types": {
                "type": "array",
                "items": {"type": "string"},
                "default": [
                    "names",
                    "email_addresses",
                    "phone_numbers",
                    "addresses",
                    "social_security_numbers",
                    "credit_card_numbers",
                ],
                "description": "Types of PII to protect",
            },
            "redaction_strategy": {
                "type": "string",
                "enum": ["mask", "remove", "generalize"],
                "default": "mask",
                "description": "How to handle detected PII",
            },
        }

```
==================================================

### File: app/templates/registry.py
```
"""
Central registry for all guardrail templates.
Implements the Factory pattern for guardrail creation.
"""

from typing import Dict, List
from app.templates.base import GuardrailStrategy
from app.templates.content_safety import ContentSafetyStrategy
from app.templates.pii_protection import PIIProtectionStrategy
from app.templates.factual_accuracy import FactualAccuracyStrategy
from app.templates.tone_control import ToneControlStrategy
from app.templates.compliance import ComplianceStrategy


class TemplateNotFoundError(Exception):
    """Raised when a template key is not found in the registry."""

    def __init__(self, key: str):
        self.key = key
        available = ", ".join(TEMPLATE_REGISTRY.keys())
        super().__init__(
            f"Template '{key}' not found. Available templates: {available}"
        )


# Global registry of all available guardrail templates
TEMPLATE_REGISTRY: Dict[str, GuardrailStrategy] = {
    "content_safety": ContentSafetyStrategy(),
    "pii_protection": PIIProtectionStrategy(),
    "factual_accuracy": FactualAccuracyStrategy(),
    "tone_control": ToneControlStrategy(),
    "compliance": ComplianceStrategy(),
}


def get_template(key: str) -> GuardrailStrategy:
    """
    Factory function to get a guardrail template by key.

    Args:
        key: The template key (e.g., 'content_safety', 'pii_protection')

    Returns:
        GuardrailStrategy: The template strategy instance

    Raises:
        TemplateNotFoundError: If the template key doesn't exist
    """
    if key not in TEMPLATE_REGISTRY:
        raise TemplateNotFoundError(key)
    return TEMPLATE_REGISTRY[key]


def list_templates() -> List[Dict[str, str]]:
    """
    Get a list of all available guardrail templates.

    Returns:
        List[dict]: List of template metadata dictionaries
    """
    return [template.to_dict() for template in TEMPLATE_REGISTRY.values()]


def get_template_keys() -> List[str]:
    """
    Get all available template keys.

    Returns:
        List[str]: List of template keys
    """
    return list(TEMPLATE_REGISTRY.keys())


def validate_template_key(key: str) -> bool:
    """
    Check if a template key is valid.

    Args:
        key: The template key to validate

    Returns:
        bool: True if the key exists, False otherwise
    """
    return key in TEMPLATE_REGISTRY

```
==================================================

### File: app/templates/tone_control.py
```
"""
Tone Control Guardrail Strategy.
Ensures appropriate tone and style in AI responses.
"""

from app.templates.base import GuardrailStrategy


class ToneControlStrategy(GuardrailStrategy):
    """
    Guardrail to control tone, style, and communication approach.
    """

    name = "tone_control"
    description = "Ensures appropriate tone, style, and communication approach in responses"

    def build_guardrail(self, user_context: str, **kwargs) -> str:
        """
        Build tone control guardrail.

        Args:
            user_context: Description of audience and communication context
            **kwargs: Additional parameters (tone, formality, brand_voice)
        """
        tone = kwargs.get("tone", "professional")
        formality = kwargs.get("formality", "balanced")
        brand_voice = kwargs.get("brand_voice", "")
        audience = kwargs.get("audience", "general")

        tone_descriptions = {
            "professional": "Courteous, competent, and business-appropriate",
            "friendly": "Warm, approachable, and conversational",
            "empathetic": "Understanding, supportive, and compassionate",
            "authoritative": "Confident, expert, and decisive",
            "casual": "Relaxed, informal, and personable",
            "educational": "Clear, patient, and instructive",
        }

        formality_levels = {
            "formal": "Use proper grammar, avoid contractions, maintain professional distance",
            "balanced": "Mix formal and conversational elements appropriately",
            "informal": "Use contractions, colloquialisms, and relaxed language",
        }

        return f"""# Tone Control Guardrail

## Context
{user_context}

## Target Tone: {tone.upper()}
{tone_descriptions.get(tone, "Professional and appropriate")}

## Formality Level: {formality.upper()}
{formality_levels.get(formality, formality_levels["balanced"])}

## Audience: {audience.title()}

{f'''## Brand Voice Guidelines
{brand_voice}
''' if brand_voice else ''}

## Communication Style Requirements

### Tone Characteristics
{self._get_tone_characteristics(tone)}

### Language Guidelines

1. **Word Choice**
{self._get_word_choice_guidelines(tone, formality)}

2. **Sentence Structure**
{self._get_sentence_structure_guidelines(formality)}

3. **Emotional Calibration**
{self._get_emotional_guidelines(tone)}

### Do's and Don'ts

#### DO:
- Match the tone consistently throughout the response
- Adapt complexity to the audience level
- Use appropriate technical language for the context
- Maintain respectful and inclusive language
- Show personality within professional boundaries

#### DON'T:
- Switch tones abruptly mid-response
- Use jargon without explanation (unless appropriate for audience)
- Be overly casual in serious situations
- Sound robotic or template-like
- Use condescending language

### Audience-Specific Adjustments

**{audience.title()} Audience:**
{self._get_audience_guidelines(audience)}

### Special Situations

**Handling Difficult Topics:**
- Increase empathy and sensitivity
- Acknowledge the seriousness appropriately
- Avoid being dismissive or overly cheerful
- Offer support and understanding

**Handling Errors or Limitations:**
- Be honest and straightforward
- Apologize when appropriate
- Offer alternatives or solutions
- Maintain positive tone while being realistic

**Handling Disagreements:**
- Stay respectful and professional
- Acknowledge different perspectives
- Focus on information, not judgment
- Use diplomatic language

### Quality Checks

Before responding, verify:
- [ ] Tone matches the specified style
- [ ] Formality level is appropriate
- [ ] Language complexity suits the audience
- [ ] No unintentional condescension or dismissiveness
- [ ] Consistent voice throughout
- [ ] Appropriate emotional calibration

### Example Phrases for {tone.title()} Tone
{self._get_example_phrases(tone)}
"""

    def _get_tone_characteristics(self, tone: str) -> str:
        """Get specific characteristics for each tone."""
        characteristics = {
            "professional": """- Competent and knowledgeable
- Respectful and courteous
- Clear and direct
- Solution-oriented
- Maintains appropriate boundaries""",
            "friendly": """- Warm and welcoming
- Approachable and personable
- Conversational and engaging
- Positive and encouraging
- Shows genuine interest""",
            "empathetic": """- Understanding and compassionate
- Validates feelings and concerns
- Patient and supportive
- Non-judgmental
- Offers comfort and reassurance""",
            "authoritative": """- Confident and decisive
- Expert and knowledgeable
- Direct and clear
- Commanding respect
- Provides strong guidance""",
            "casual": """- Relaxed and informal
- Uses everyday language
- Conversational and natural
- Approachable and friendly
- Comfortable and easygoing""",
            "educational": """- Clear and explanatory
- Patient and thorough
- Encourages learning
- Breaks down complex concepts
- Supportive and non-judgmental""",
        }
        return characteristics.get(tone, characteristics["professional"])

    def _get_word_choice_guidelines(self, tone: str, formality: str) -> str:
        """Get word choice guidelines based on tone and formality."""
        if formality == "formal":
            return """- Use complete words (do not → do not)
- Prefer sophisticated vocabulary
- Avoid slang and colloquialisms
- Use precise, technical terms when appropriate"""
        elif formality == "informal":
            return """- Use contractions freely (don't, can't, we'll)
- Use everyday vocabulary
- Include appropriate colloquialisms
- Keep language accessible"""
        else:
            return """- Use contractions moderately
- Balance sophistication with accessibility
- Mix formal and conversational elements
- Adjust based on context"""

    def _get_sentence_structure_guidelines(self, formality: str) -> str:
        """Get sentence structure guidelines."""
        structures = {
            "formal": """- Use complete, well-structured sentences
- Prefer longer, more complex sentences
- Follow strict grammatical rules
- Use passive voice when appropriate""",
            "balanced": """- Mix simple and complex sentences
- Vary sentence length for flow
- Follow standard grammar with some flexibility
- Primarily use active voice""",
            "informal": """- Use short, punchy sentences
- Fragment sentences occasionally for effect
- Be flexible with grammar rules
- Always use active voice""",
        }
        return structures.get(formality, structures["balanced"])

    def _get_emotional_guidelines(self, tone: str) -> str:
        """Get emotional calibration guidelines."""
        emotional = {
            "professional": "Measured and controlled; show appropriate concern without over-emotion",
            "friendly": "Warm and positive; express genuine interest and enthusiasm",
            "empathetic": "High emotional awareness; validate feelings and show understanding",
            "authoritative": "Confident and composed; project calm expertise",
            "casual": "Relaxed and natural; show personality and authentic reactions",
            "educational": "Patient and encouraging; celebrate learning moments",
        }
        return emotional.get(tone, "Appropriate to context and audience")

    def _get_audience_guidelines(self, audience: str) -> str:
        """Get audience-specific guidelines."""
        guidelines = {
            "technical": "Use industry terminology; assume baseline knowledge; be precise",
            "general": "Explain technical terms; assume diverse knowledge levels; be clear",
            "executive": "Focus on high-level insights; be concise; emphasize impact",
            "customer": "Be helpful and patient; avoid jargon; focus on solutions",
            "internal": "Use company-specific terms; be direct; assume context",
            "academic": "Use scholarly tone; cite sources; be thorough and precise",
        }
        return guidelines.get(audience, "Adapt to audience knowledge and needs")

    def _get_example_phrases(self, tone: str) -> str:
        """Get example phrases for each tone."""
        examples = {
            "professional": """✓ "I'd be happy to assist you with that."
✓ "Let me clarify that for you."
✓ "I understand your concern regarding..."
✓ "I recommend the following approach..."
✗ "Hey! No worries, I got you!"
✗ "That's a dumb question, but..."
✗ "Whatever you want, I guess..."
""",
            "friendly": """✓ "I'd love to help you with that!"
✓ "Great question! Here's what I think..."
✓ "Thanks for sharing that with me!"
✓ "Let's figure this out together."
✗ "As per your request, I shall proceed..."
✗ "Your inquiry has been noted."
✗ "I'm just a bot, so..."
""",
            "empathetic": """✓ "I understand how frustrating that must be."
✓ "That sounds really challenging."
✓ "Your feelings about this are completely valid."
✓ "I'm here to support you through this."
✗ "Just do it this way instead."
✗ "That's not really a big deal."
✗ "Everyone has that problem."
""",
            "authoritative": """✓ "The best approach is..."
✓ "Based on industry standards..."
✓ "You should implement..."
✓ "The correct method is..."
✗ "Maybe you could try...?"
✗ "I'm not sure, but possibly..."
✗ "Whatever works for you..."
""",
            "casual": """✓ "No worries, I can help with that!"
✓ "Yeah, that's a common thing."
✓ "Let's dive into this!"
✓ "Here's the deal..."
✗ "I shall endeavor to assist."
✗ "Per your request..."
✗ "One must consider..."
""",
            "educational": """✓ "Let me break that down for you."
✓ "Here's how this works..."
✓ "Think of it this way..."
✓ "Great question! This is an important concept."
✗ "Obviously, anyone would know..."
✗ "This is simple, just..."
✗ "I already explained that..."
""",
        }
        return examples.get(tone, examples["professional"])

    def get_parameters(self):
        return {
            "tone": {
                "type": "string",
                "enum": ["professional", "friendly", "empathetic", "authoritative", "casual", "educational"],
                "default": "professional",
                "description": "Overall tone of communication",
            },
            "formality": {
                "type": "string",
                "enum": ["formal", "balanced", "informal"],
                "default": "balanced",
                "description": "Level of formality in language",
            },
            "brand_voice": {
                "type": "string",
                "default": "",
                "description": "Optional brand voice guidelines",
            },
            "audience": {
                "type": "string",
                "enum": ["general", "technical", "executive", "customer", "internal", "academic"],
                "default": "general",
                "description": "Target audience type",
            },
        }

```
==================================================

### File: requirements.txt
```
# FastAPI & Server
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
pydantic-settings==2.1.0

# Database
sqlalchemy==2.0.25
asyncpg==0.29.0

# Message Queue
nats-py==2.6.0

# LLM Providers
openai==1.12.0
anthropic==0.18.1

# Utilities
python-dotenv==1.0.0
httpx==0.26.0
tenacity==8.2.3

# Logging & Monitoring
structlog==24.1.0
prometheus-client==0.19.0

# Testing
pytest==7.4.4
pytest-asyncio==0.23.3
pytest-cov==4.1.0

```
==================================================
