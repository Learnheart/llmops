"""
SQLAlchemy ORM models for Guardrails Service.
Defines database schema for guardrail generations, variants, and history.
"""

import enum
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncAttrs, create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, relationship
from app.config import get_settings


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all database models."""
    pass


class VariantStatus(str, enum.Enum):
    """Status of a guardrail variant."""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class HistoryAction(str, enum.Enum):
    """Types of actions that can be logged in history."""
    CREATED = "created"
    UPDATED = "updated"
    ACTIVATED = "activated"
    DEACTIVATED = "deactivated"
    ARCHIVED = "archived"
    STATUS_CHANGED = "status_changed"


class GuardrailGeneration(Base):
    """
    Stores generated guardrails from templates.

    This is the output of applying a guardrail template with specific parameters.
    It represents a single guardrail generation that can be used or customized.
    """
    __tablename__ = "guardrail_generations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    template_key = Column(String(100), nullable=False, index=True)
    user_context = Column(Text, nullable=False)
    generated_guardrail = Column(Text, nullable=False)
    parameters = Column(JSON, nullable=True)  # Template-specific parameters
    metadata = Column(JSON, nullable=True)  # Additional metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    variants = relationship(
        "GuardrailVariant",
        back_populates="generation",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<GuardrailGeneration(id={self.id}, template={self.template_key}, user={self.user_id})>"


class GuardrailVariant(Base):
    """
    User-customized guardrails with versioning support.

    Variants allow users to customize and save specific versions of guardrails.
    Each update creates a new version, maintaining a complete history.
    """
    __tablename__ = "guardrail_variants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    generation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("guardrail_generations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    guardrail_content = Column(Text, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    status = Column(
        Enum(VariantStatus),
        default=VariantStatus.DRAFT,
        nullable=False,
        index=True,
    )
    tags = Column(JSON, nullable=True)  # User-defined tags for organization
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    generation = relationship("GuardrailGeneration", back_populates="variants")
    history = relationship(
        "GuardrailVariantHistory",
        back_populates="variant",
        cascade="all, delete-orphan",
        order_by="GuardrailVariantHistory.created_at.desc()",
    )

    def __repr__(self):
        return f"<GuardrailVariant(id={self.id}, name={self.name}, version={self.version}, status={self.status})>"


class GuardrailVariantHistory(Base):
    """
    Audit log for all guardrail variant changes.

    Maintains a complete history of all changes to variants for compliance,
    debugging, and rollback capabilities.
    """
    __tablename__ = "guardrail_variant_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    variant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("guardrail_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(String(255), nullable=False, index=True)
    action = Column(Enum(HistoryAction), nullable=False)
    old_content = Column(Text, nullable=True)
    new_content = Column(Text, nullable=True)
    old_version = Column(Integer, nullable=True)
    new_version = Column(Integer, nullable=True)
    old_status = Column(Enum(VariantStatus), nullable=True)
    new_status = Column(Enum(VariantStatus), nullable=True)
    change_summary = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    variant = relationship("GuardrailVariant", back_populates="history")

    def __repr__(self):
        return f"<GuardrailVariantHistory(id={self.id}, variant={self.variant_id}, action={self.action})>"


# Database engine and session management
settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
    pool_pre_ping=settings.db_pool_pre_ping,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """
    Dependency for getting database sessions.

    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """
    Initialize database tables.
    Creates all tables defined in Base metadata.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """
    Close database connections.
    Call during application shutdown.
    """
    await engine.dispose()
