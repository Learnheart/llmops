"""PostgreSQL connection."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://llmops:llmops_secret@localhost:5432/llmops"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def get_db():
    """Dependency để inject DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
