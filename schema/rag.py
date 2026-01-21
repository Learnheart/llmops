"""Pydantic models for RAG module."""

from enum import Enum
from datetime import datetime
from pydantic import BaseModel


class OriginType(str, Enum):
    """Nguồn gốc tài liệu trong SSOT"""
    SYNC = "sync"
    UPLOAD = "upload"


class DocumentInfo(BaseModel):
    """Thông tin một tài liệu trong SSOT"""
    path: str
    filename: str
    size: int
    origin_type: OriginType
    source_type: str | None
    last_modified: datetime
    content_type: str | None


class DocumentListResponse(BaseModel):
    """Response cho API list documents"""
    documents: list[DocumentInfo]
    total: int


class DocumentUploadResponse(BaseModel):
    """Response cho API upload document"""
    path: str
    filename: str
    size: int


class RemoteFile(BaseModel):
    """Thông tin file từ external source (dùng cho sync job)"""
    path: str
    filename: str
    size: int
    modified_at: datetime
    content_type: str | None = None
