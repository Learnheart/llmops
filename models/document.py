"""Document model."""

import uuid
import enum
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from db.postgres import Base


class OriginType(str, enum.Enum):
    """Nguồn gốc document."""
    SYNC = "sync"
    UPLOAD = "upload"


class Document(Base):
    """Document metadata trong DB."""

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    knowledge_base_id = Column(String(255), nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # File info
    filename = Column(String(255), nullable=False)
    storage_path = Column(String(512), nullable=False)
    file_size = Column(Integer)
    content_type = Column(String(100))

    # Origin
    origin_type = Column(Enum(OriginType), default=OriginType.UPLOAD)
    source_type = Column(String(50))  # github, confluence... (null nếu upload)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
