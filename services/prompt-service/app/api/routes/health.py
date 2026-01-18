"""Health check endpoints."""

import time
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.schemas import HealthResponse, DetailedHealthResponse
from app import __version__

router = APIRouter(tags=["health"])

# Track startup time
_startup_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="prompt-service",
        version=__version__,
        database="unknown",
    )


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """Detailed health check with database connectivity."""
    uptime = time.time() - _startup_time
    db_status = "healthy"
    db_latency = None

    try:
        # Test database connection
        start = time.time()
        await db.execute(text("SELECT 1"))
        db_latency = (time.time() - start) * 1000  # Convert to ms
    except Exception:
        db_status = "unhealthy"

    return DetailedHealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        service="prompt-service",
        version=__version__,
        database=db_status,
        uptime=uptime,
        database_latency_ms=db_latency,
    )


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Kubernetes readiness probe."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        return {"status": "not_ready"}, 503


@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe."""
    return {"status": "alive"}
