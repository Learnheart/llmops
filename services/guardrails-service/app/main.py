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
