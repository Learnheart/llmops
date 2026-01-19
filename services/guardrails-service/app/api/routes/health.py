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
