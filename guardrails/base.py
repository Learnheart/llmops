"""Base class for guardrails."""

from abc import ABC, abstractmethod
from typing import Any

from schema.guardrails import GuardrailResult, GuardrailAction


class BaseGuardrail(ABC):
    """Abstract base class for all guardrails."""

    def __init__(self, config: dict[str, Any] = None):
        """
        Initialize guardrail with config.

        Args:
            config: Type-specific configuration. If None, uses default_config.
        """
        self.config = {**self.default_config, **(config or {})}

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the guardrail."""
        pass

    @property
    @abstractmethod
    def guardrail_type(self) -> str:
        """Type identifier for this guardrail."""
        pass

    @property
    @abstractmethod
    def default_config(self) -> dict[str, Any]:
        """Default configuration for this guardrail."""
        pass

    @abstractmethod
    def check(self, text: str) -> GuardrailResult:
        """
        Execute guardrail check on text.

        Args:
            text: Input text to check

        Returns:
            GuardrailResult with check outcome
        """
        pass

    def _pass_result(self, text: str, message: str = "Check passed") -> GuardrailResult:
        """Helper to create a passing result."""
        return GuardrailResult(
            passed=True,
            action_taken=GuardrailAction.PASS,
            original_text=text,
            processed_text=text,
            message=message,
            details={},
        )

    def _fail_result(
        self,
        text: str,
        action: GuardrailAction,
        message: str,
        processed_text: str = None,
        details: dict = None,
    ) -> GuardrailResult:
        """Helper to create a failing result."""
        return GuardrailResult(
            passed=False,
            action_taken=action,
            original_text=text,
            processed_text=processed_text or text,
            message=message,
            details=details or {},
        )
