"""Health check endpoints."""

import time
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.database import get_db
from app.models.schemas import HealthResponse, DetailedHealthResponse, StorageStatus

router = APIRouter()
settings = get_settings()

# Track service start time for uptime calculation
_start_time = datetime.utcnow()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint."""
    return HealthResponse(
        status="healthy",
        service=settings.service_name,
        version="0.1.0",
    )


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """Detailed health check with storage status."""
    uptime = (datetime.utcnow() - _start_time).total_seconds()
    storage_status = {}

    # Check PostgreSQL
    try:
        start = time.time()
        await db.execute(text("SELECT 1"))
        latency = (time.time() - start) * 1000
        storage_status["postgres"] = StorageStatus(
            name="PostgreSQL",
            status="healthy",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        storage_status["postgres"] = StorageStatus(
            name="PostgreSQL",
            status="unhealthy",
            error=str(e),
        )

    # Determine overall status
    overall_status = "healthy"
    for status in storage_status.values():
        if status.status == "unhealthy":
            overall_status = "degraded"
            break

    return DetailedHealthResponse(
        status=overall_status,
        service=settings.service_name,
        version="0.1.0",
        uptime_seconds=uptime,
        storage=storage_status,
    )


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Kubernetes readiness probe."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        return {"status": "not_ready", "error": str(e)}


@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe."""
    return {"status": "alive"}
