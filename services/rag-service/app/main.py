"""FastAPI application entry point for RAG Service."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models.database import init_db, close_db
from app.api.routes import health, components, pipelines, ingestion, retrieval

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


app = FastAPI(
    title="RAG Service",
    description="Document ingestion and retrieval pipeline service for LLMOps Platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(
    components.router,
    prefix=f"{settings.api_v1_prefix}/components",
    tags=["components"],
)
app.include_router(
    pipelines.router,
    prefix=f"{settings.api_v1_prefix}/pipelines",
    tags=["pipelines"],
)
app.include_router(
    ingestion.router,
    prefix=f"{settings.api_v1_prefix}/ingest",
    tags=["ingestion"],
)
app.include_router(
    retrieval.router,
    prefix=f"{settings.api_v1_prefix}/retrieve",
    tags=["retrieval"],
)


@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": settings.service_name,
        "version": "0.1.0",
        "docs": "/docs",
    }
