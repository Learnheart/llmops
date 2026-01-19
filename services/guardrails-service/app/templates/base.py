"""
Base class for guardrail template strategies.
All guardrail templates must inherit from GuardrailStrategy.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


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
