"""Pydantic models for Model Selector module."""

from pydantic import BaseModel


class ModelSelectorOutput(BaseModel):
    """Output from model selector."""
    selected: str       # Tên model được chọn
    reasoning: str      # Giải thích lựa chọn
