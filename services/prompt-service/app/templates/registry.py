"""Template registry - Central registry for all prompt strategies."""

from typing import Dict, List

from app.templates.base import PromptStrategy
from app.templates.concise import ConciseStrategy
from app.templates.detailed import DetailedStrategy
from app.templates.step_by_step import StepByStepStrategy
from app.templates.few_shot import FewShotStrategy


class TemplateNotFoundError(Exception):
    """Raised when a template key is not found in the registry."""

    def __init__(self, key: str):
        self.key = key
        super().__init__(f"Template '{key}' not found in registry")


# Registry of all available prompt strategies
# This is the single source of truth for templates
TEMPLATE_REGISTRY: Dict[str, PromptStrategy] = {
    "concise": ConciseStrategy(),
    "detailed": DetailedStrategy(),
    "step_by_step": StepByStepStrategy(),
    "few_shot": FewShotStrategy(),
}


def get_template(key: str) -> PromptStrategy:
    """Get a template strategy by key.

    Args:
        key: The template key (e.g., "concise", "detailed")

    Returns:
        The PromptStrategy instance

    Raises:
        TemplateNotFoundError: If the key is not found
    """
    if key not in TEMPLATE_REGISTRY:
        raise TemplateNotFoundError(key)
    return TEMPLATE_REGISTRY[key]


def list_templates() -> List[dict]:
    """List all available templates.

    Returns:
        List of template dictionaries with key, name, and description
    """
    return [strategy.to_dict() for strategy in TEMPLATE_REGISTRY.values()]


def get_template_keys() -> List[str]:
    """Get all available template keys.

    Returns:
        List of template keys
    """
    return list(TEMPLATE_REGISTRY.keys())


def validate_template_keys(keys: List[str]) -> List[str]:
    """Validate a list of template keys.

    Args:
        keys: List of template keys to validate

    Returns:
        List of invalid keys (empty if all valid)
    """
    return [key for key in keys if key not in TEMPLATE_REGISTRY]
