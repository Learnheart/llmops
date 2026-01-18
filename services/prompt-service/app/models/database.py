"""Database configuration and models."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum

from app.config import get_settings


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class VariantStatus(enum.Enum):
    """Status of a prompt variant."""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class HistoryAction(enum.Enum):
    """Action type for history records."""
    CREATED = "created"
    UPDATED = "updated"
    ACTIVATED = "activated"
    DEACTIVATED = "deactivated"
    ARCHIVED = "archived"


class PromptGeneration(Base):
    """Model for storing generated prompts."""

    __tablename__ = "prompt_generations"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    template_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    agent_instruction: Mapped[str] = mapped_column(Text, nullable=False)
    generated_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    variants: Mapped[list["PromptVariant"]] = relationship(
        "PromptVariant",
        back_populates="generation",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<PromptGeneration(id={self.id}, template_key={self.template_key})>"


class PromptVariant(Base):
    """Model for storing prompt variants with versioning."""

    __tablename__ = "prompt_variants"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    generation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("prompt_generations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[VariantStatus] = mapped_column(
        SQLEnum(VariantStatus),
        default=VariantStatus.DRAFT,
        nullable=False
    )
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    generation: Mapped["PromptGeneration"] = relationship(
        "PromptGeneration",
        back_populates="variants"
    )
    history: Mapped[list["PromptVariantHistory"]] = relationship(
        "PromptVariantHistory",
        back_populates="variant",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<PromptVariant(id={self.id}, name={self.name}, version={self.version})>"


class PromptVariantHistory(Base):
    """Audit log for prompt variant changes."""

    __tablename__ = "prompt_variant_history"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    variant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("prompt_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    action: Mapped[HistoryAction] = mapped_column(
        SQLEnum(HistoryAction),
        nullable=False
    )
    old_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    old_version: Mapped[Optional[int]] = mapped_column(nullable=True)
    new_version: Mapped[Optional[int]] = mapped_column(nullable=True)
    change_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    variant: Mapped["PromptVariant"] = relationship(
        "PromptVariant",
        back_populates="history"
    )

    def __repr__(self) -> str:
        return f"<PromptVariantHistory(id={self.id}, action={self.action})>"


# Database engine and session
settings = get_settings()
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """Dependency for getting database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections."""
    await engine.dispose()
