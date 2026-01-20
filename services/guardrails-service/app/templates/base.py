"""
Base class for guardrail template strategies.
All guardrail templates must inherit from GuardrailStrategy.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, List


class InvalidParameterError(Exception):
    """Raised when a parameter fails validation."""

    def __init__(self, message: str, parameter: Optional[str] = None):
        self.parameter = parameter
        super().__init__(message)


class GuardrailStrategy(ABC):
    """
    Abstract base class for guardrail generation strategies.

    Each strategy represents a different type of guardrail that can be
    applied to LLM interactions to ensure safety, compliance, or quality.
    """

    name: str
    description: str

    @abstractmethod
    def build_guardrail(self, user_context: str, **kwargs) -> str:
        """
        Build the guardrail prompt/rules based on user context.

        Args:
            user_context: User-provided context or requirements for the guardrail
            **kwargs: Additional parameters specific to the guardrail type

        Returns:
            str: The generated guardrail prompt/rules
        """
        pass

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert strategy to dictionary representation.

        Returns:
            dict: Strategy metadata including key, name, and description
        """
        return {
            "key": self.name,
            "name": self.name.replace("_", " ").title(),
            "description": self.description,
        }

    def get_parameters(self) -> Dict[str, Any]:
        """
        Get the parameters that this guardrail accepts.

        Returns:
            dict: Parameter definitions with types and descriptions
        """
        return {}

    def validate_parameters(self, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate parameters against the defined schema.

        Checks:
        - Unknown parameters (not in schema)
        - Type validation (string, array, etc.)
        - Enum validation (must be one of allowed values)
        - Required vs optional parameters

        Args:
            params: Parameters to validate

        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        schema = self.get_parameters()

        for key, value in params.items():
            if key not in schema:
                return False, f"Unknown parameter: '{key}'. Valid parameters: {list(schema.keys())}"

            param_schema = schema[key]
            param_type = param_schema.get("type")

            # Type validation
            if param_type == "string":
                if not isinstance(value, str):
                    return False, f"Parameter '{key}' must be a string, got {type(value).__name__}"
            elif param_type == "array":
                if not isinstance(value, list):
                    return False, f"Parameter '{key}' must be an array, got {type(value).__name__}"
                # Validate array item types if specified
                item_type = param_schema.get("items", {}).get("type")
                if item_type == "string":
                    for i, item in enumerate(value):
                        if not isinstance(item, str):
                            return False, f"Parameter '{key}[{i}]' must be a string, got {type(item).__name__}"
            elif param_type == "boolean":
                if not isinstance(value, bool):
                    return False, f"Parameter '{key}' must be a boolean, got {type(value).__name__}"
            elif param_type == "integer":
                if not isinstance(value, int) or isinstance(value, bool):
                    return False, f"Parameter '{key}' must be an integer, got {type(value).__name__}"
            elif param_type == "number":
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    return False, f"Parameter '{key}' must be a number, got {type(value).__name__}"

            # Enum validation
            if "enum" in param_schema and value not in param_schema["enum"]:
                return False, f"Parameter '{key}' must be one of {param_schema['enum']}, got '{value}'"

        return True, None

    def get_validated_params(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Validate parameters and return them with defaults applied.

        Args:
            params: Parameters provided by user (can be None)

        Returns:
            Dict[str, Any]: Validated parameters with defaults

        Raises:
            InvalidParameterError: If validation fails
        """
        params = params or {}
        schema = self.get_parameters()

        # Validate provided params
        is_valid, error = self.validate_parameters(params)
        if not is_valid:
            raise InvalidParameterError(error)

        # Apply defaults for missing parameters
        result = {}
        for key, param_schema in schema.items():
            if key in params:
                result[key] = params[key]
            elif "default" in param_schema:
                result[key] = param_schema["default"]

        return result
