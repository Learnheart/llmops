"""
Central registry for all guardrail templates.
Implements the Factory pattern for guardrail creation.
"""

from typing import Dict, List
from app.templates.base import GuardrailStrategy
from app.templates.content_safety import ContentSafetyStrategy
from app.templates.pii_protection import PIIProtectionStrategy
from app.templates.factual_accuracy import FactualAccuracyStrategy
from app.templates.tone_control import ToneControlStrategy
from app.templates.compliance import ComplianceStrategy


class TemplateNotFoundError(Exception):
    """Raised when a template key is not found in the registry."""

    def __init__(self, key: str):
        self.key = key
        available = ", ".join(TEMPLATE_REGISTRY.keys())
        super().__init__(
            f"Template '{key}' not found. Available templates: {available}"
        )


# Global registry of all available guardrail templates
TEMPLATE_REGISTRY: Dict[str, GuardrailStrategy] = {
    "content_safety": ContentSafetyStrategy(),
    "pii_protection": PIIProtectionStrategy(),
    "factual_accuracy": FactualAccuracyStrategy(),
    "tone_control": ToneControlStrategy(),
    "compliance": ComplianceStrategy(),
}


def get_template(key: str) -> GuardrailStrategy:
    """
    Factory function to get a guardrail template by key.

    Args:
        key: The template key (e.g., 'content_safety', 'pii_protection')

    Returns:
        GuardrailStrategy: The template strategy instance

    Raises:
        TemplateNotFoundError: If the template key doesn't exist
    """
    if key not in TEMPLATE_REGISTRY:
        raise TemplateNotFoundError(key)
    return TEMPLATE_REGISTRY[key]


def list_templates() -> List[Dict[str, str]]:
    """
    Get a list of all available guardrail templates.

    Returns:
        List[dict]: List of template metadata dictionaries
    """
    return [template.to_dict() for template in TEMPLATE_REGISTRY.values()]


def get_template_keys() -> List[str]:
    """
    Get all available template keys.

    Returns:
        List[str]: List of template keys
    """
    return list(TEMPLATE_REGISTRY.keys())


def validate_template_key(key: str) -> bool:
    """
    Check if a template key is valid.

    Args:
        key: The template key to validate

    Returns:
        bool: True if the key exists, False otherwise
    """
    return key in TEMPLATE_REGISTRY
