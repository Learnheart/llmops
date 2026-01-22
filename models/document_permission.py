"""DocumentPermission model."""

import uuid
import enum
from sqlalchemy import Column, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from db.postgres import Base


class Permission(str, enum.Enum):
    """Loại permission."""
    READ = "read"
    WRITE = "write"


class DocumentPermission(Base):
    """Permission cho tenant khác truy cập document."""

    __tablename__ = "document_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    permission = Column(Enum(Permission), default=Permission.READ)
    created_at = Column(DateTime, server_default=func.now())
