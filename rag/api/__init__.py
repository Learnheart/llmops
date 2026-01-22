"""API routers."""

from fastapi import APIRouter
from rag.api.documents import router as documents_router

router = APIRouter(prefix="/api/v1")
router.include_router(documents_router)
