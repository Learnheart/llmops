"""Prompt Templates - Factory Strategy Pattern."""

from app.templates.base import PromptStrategy
from app.templates.registry import (
    TEMPLATE_REGISTRY,
    get_template,
    list_templates,
    TemplateNotFoundError,
)

__all__ = [
    "PromptStrategy",
    "TEMPLATE_REGISTRY",
    "get_template",
    "list_templates",
    "TemplateNotFoundError",
]
