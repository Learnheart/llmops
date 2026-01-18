"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routes import health, templates, generations, variants, prompts
from app.models.database import init_db, close_db


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


app = FastAPI(
    title="Prompt Service",
    description="LLMOps Platform - Prompt Generation and Management Service",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(templates.router, prefix="/api/v1", tags=["templates"])
app.include_router(prompts.router, prefix="/api/v1", tags=["prompts"])
app.include_router(generations.router, prefix="/api/v1", tags=["generations"])
app.include_router(variants.router, prefix="/api/v1", tags=["variants"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=True,
    )
