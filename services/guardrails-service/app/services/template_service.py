"""
Template Service - manages guardrail template operations.
Handles template retrieval, validation, and preview.
"""

from typing import Dict, List, Any, Optional

from app.templates.registry import (
    get_template,
    list_templates,
    get_template_keys,
    validate_template_key,
    TemplateNotFoundError,
)
from app.templates.base import GuardrailStrategy, InvalidParameterError


class TemplateService:
    """
    Service for guardrail template operations.

    This service reads templates from code (registry) and does NOT
    interact with the database. It's stateless and provides template
    information and generation capabilities.
    """

    def list_all_templates(self) -> List[Dict[str, Any]]:
        """
        Get all available guardrail templates.

        Returns:
            List[dict]: List of template metadata
        """
        return list_templates()

    def get_template_keys(self) -> List[str]:
        """
        Get all available template keys.

        Returns:
            List[str]: List of template keys
        """
        return get_template_keys()

    def get_template_info(self, template_key: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific template.

        Args:
            template_key: Template key

        Returns:
            dict: Template information including parameters

        Raises:
            TemplateNotFoundError: If template doesn't exist
        """
        template = get_template(template_key)
        info = template.to_dict()
        info["parameters"] = template.get_parameters()
        return info

    def validate_template_key(self, template_key: str) -> bool:
        """
        Validate that a template key exists.

        Args:
            template_key: Template key to validate

        Returns:
            bool: True if valid, False otherwise
        """
        return validate_template_key(template_key)

    def validate_parameters(
        self,
        template_key: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Validate parameters for a specific template.

        Args:
            template_key: Template to validate against
            parameters: Parameters to validate

        Returns:
            tuple[bool, Optional[str]]: (is_valid, error_message)

        Raises:
            TemplateNotFoundError: If template doesn't exist
        """
        template = get_template(template_key)
        return template.validate_parameters(parameters or {})

    def build_guardrail(
        self,
        template_key: str,
        user_context: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build a guardrail using the specified template.

        Parameters are validated before building.

        Args:
            template_key: Template to use
            user_context: User-provided context
            parameters: Template-specific parameters

        Returns:
            str: Generated guardrail content

        Raises:
            TemplateNotFoundError: If template doesn't exist
            InvalidParameterError: If parameters fail validation
        """
        template = get_template(template_key)

        # Validate and get params with defaults
        validated_params = template.get_validated_params(parameters)

        return template.build_guardrail(user_context, **validated_params)

    def preview_guardrail(
        self,
        template_key: str,
        user_context: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Preview a guardrail without saving to database.

        Args:
            template_key: Template to use
            user_context: User-provided context
            parameters: Template-specific parameters

        Returns:
            dict: Preview information including generated guardrail

        Raises:
            TemplateNotFoundError: If template doesn't exist
        """
        guardrail_content = self.build_guardrail(template_key, user_context, parameters)
        template = get_template(template_key)

        return {
            "template_key": template_key,
            "template_name": template.name.replace("_", " ").title(),
            "generated_guardrail": guardrail_content,
            "parameters": parameters,
        }

    def get_template_count(self) -> int:
        """
        Get the total number of available templates.

        Returns:
            int: Number of templates
        """
        return len(get_template_keys())
