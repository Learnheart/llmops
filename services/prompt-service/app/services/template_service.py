"""Template service - handles template operations (reads from CODE)."""

from typing import List, Optional

from app.templates.registry import (
    TEMPLATE_REGISTRY,
    get_template,
    list_templates,
    get_template_keys,
    validate_template_keys,
    TemplateNotFoundError,
)
from app.templates.base import PromptStrategy
from app.models.schemas import TemplateInfo


class TemplateService:
    """Service for template operations.

    This service reads templates from CODE (not database).
    Templates are managed by developers and defined in app/templates/.
    """

    def get_template(self, key: str) -> PromptStrategy:
        """Get a template strategy by key.

        Args:
            key: The template key (e.g., "concise", "detailed")

        Returns:
            The PromptStrategy instance

        Raises:
            TemplateNotFoundError: If the key is not found
        """
        return get_template(key)

    def list_templates(self) -> List[TemplateInfo]:
        """List all available templates.

        Returns:
            List of TemplateInfo objects
        """
        templates = list_templates()
        return [
            TemplateInfo(
                key=t["key"],
                name=t["name"],
                description=t["description"],
            )
            for t in templates
        ]

    def get_template_keys(self) -> List[str]:
        """Get all available template keys.

        Returns:
            List of template keys
        """
        return get_template_keys()

    def validate_template_key(self, key: str) -> bool:
        """Check if a template key is valid.

        Args:
            key: The template key to validate

        Returns:
            True if valid, False otherwise
        """
        return key in TEMPLATE_REGISTRY

    def validate_template_keys(self, keys: List[str]) -> List[str]:
        """Validate multiple template keys.

        Args:
            keys: List of template keys to validate

        Returns:
            List of invalid keys (empty if all valid)
        """
        return validate_template_keys(keys)

    def build_prompt(self, key: str, agent_instruction: str) -> str:
        """Build a prompt using a template.

        Args:
            key: The template key
            agent_instruction: The instruction to incorporate

        Returns:
            The generated prompt string

        Raises:
            TemplateNotFoundError: If the key is not found
        """
        template = self.get_template(key)
        return template.build_prompt(agent_instruction)

    def get_template_info(self, key: str) -> Optional[TemplateInfo]:
        """Get detailed info about a specific template.

        Args:
            key: The template key

        Returns:
            TemplateInfo object or None if not found
        """
        try:
            template = self.get_template(key)
            return TemplateInfo(
                key=template.key,
                name=template.name,
                description=template.description,
            )
        except TemplateNotFoundError:
            return None
