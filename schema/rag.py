"""Pydantic schemas for RAG module."""

from enum import Enum
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class OriginType(str, Enum):
    """Nguồn gốc document."""
    SYNC = "sync"
    UPLOAD = "upload"


class Permission(str, Enum):
    """Loại permission."""
    READ = "read"
    WRITE = "write"


# ============ Response Schemas ============

class DocumentResponse(BaseModel):
    """Response cho 1 document."""
    id: UUID
    tenant_id: UUID
    knowledge_base_id: str
    owner_id: UUID
    filename: str
    storage_path: str
    file_size: int | None
    content_type: str | None
    origin_type: OriginType
    source_type: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Response danh sách documents."""
    documents: list[DocumentResponse]
    total: int


class DocumentUploadResponse(BaseModel):
    """Response sau khi upload."""
    id: UUID
    filename: str
    storage_path: str
    file_size: int


# ============ Internal Schemas ============

class RemoteFile(BaseModel):
    """File từ external source (cho sync job)."""
    path: str
    filename: str
    size: int
    modified_at: datetime
    content_type: str | None = None
