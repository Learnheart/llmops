"""Guardrails Executor - Runtime execution of guardrails pipeline."""

from typing import Optional

from guardrails.base import BaseGuardrail
from guardrails.input import (
    PIIDetectionGuardrail,
    InjectionPreventionGuardrail,
    ValidationSanitizeGuardrail,
    TopicClassificationGuardrail,
)
from guardrails.output import (
    ContentFilteringGuardrail,
    FormatValidationGuardrail,
    SafetyScoringGuardrail,
)
from schema.guardrails import (
    GuardrailAction,
    GuardrailResult,
    GuardrailConfig,
    PipelineResult,
)


# Registry mapping type names to classes
GUARDRAIL_REGISTRY: dict[str, type[BaseGuardrail]] = {
    # Input guardrails
    "validation_sanitize": ValidationSanitizeGuardrail,
    "pii_detection": PIIDetectionGuardrail,
    "injection_prevention": InjectionPreventionGuardrail,
    "topic_classification": TopicClassificationGuardrail,
    # Output guardrails
    "content_filtering": ContentFilteringGuardrail,
    "format_validation": FormatValidationGuardrail,
    "safety_scoring": SafetyScoringGuardrail,
}


class GuardrailsExecutor:
    """
    Execute guardrails pipeline on input/output text.

    Usage:
        # From guardrails generator output
        executor = GuardrailsExecutor(
            input_guardrails=["pii_detection", "injection_prevention"],
            output_guardrails=["content_filtering"]
        )

        # Process input
        result = executor.check_input(user_message)
        if result.passed:
            safe_input = result.processed_text
        else:
            # Handle blocked input

        # Process output
        result = executor.check_output(llm_response)
        safe_output = result.processed_text
    """

    def __init__(
        self,
        input_guardrails: list[str | GuardrailConfig] = None,
        output_guardrails: list[str | GuardrailConfig] = None,
    ):
        """
        Initialize executor with guardrails configuration.

        Args:
            input_guardrails: List of guardrail types or configs for input
            output_guardrails: List of guardrail types or configs for output
        """
        self._input_guards: list[BaseGuardrail] = []
        self._output_guards: list[BaseGuardrail] = []

        # Initialize input guardrails
        for guard in input_guardrails or []:
            self._input_guards.append(self._create_guardrail(guard))

        # Initialize output guardrails
        for guard in output_guardrails or []:
            self._output_guards.append(self._create_guardrail(guard))

    def _create_guardrail(self, guard: str | GuardrailConfig) -> BaseGuardrail:
        """Create guardrail instance from type name or config."""
        if isinstance(guard, str):
            guard_type = guard
            config = {}
        else:
            guard_type = guard.type
            config = guard.config

        guard_class = GUARDRAIL_REGISTRY.get(guard_type)
        if guard_class is None:
            raise ValueError(
                f"Unknown guardrail type: {guard_type}. "
                f"Available: {list(GUARDRAIL_REGISTRY.keys())}"
            )

        return guard_class(config=config)

    def check_input(self, text: str) -> PipelineResult:
        """
        Run input guardrails pipeline.

        Args:
            text: User input text

        Returns:
            PipelineResult with overall status and processed text
        """
        return self._run_pipeline(text, self._input_guards)

    def check_output(self, text: str) -> PipelineResult:
        """
        Run output guardrails pipeline.

        Args:
            text: LLM output text

        Returns:
            PipelineResult with overall status and processed text
        """
        return self._run_pipeline(text, self._output_guards)

    def _run_pipeline(
        self,
        text: str,
        guards: list[BaseGuardrail]
    ) -> PipelineResult:
        """Run a sequence of guardrails on text."""
        results: list[GuardrailResult] = []
        current_text = text
        blocked_by: Optional[str] = None

        for guard in guards:
            result = guard.check(current_text)
            results.append(result)

            # If rejected, stop pipeline
            if result.action_taken == GuardrailAction.REJECT:
                blocked_by = guard.guardrail_type
                return PipelineResult(
                    passed=False,
                    original_text=text,
                    processed_text=current_text,
                    results=results,
                    blocked_by=blocked_by,
                )

            # Update text if processed
            if result.processed_text:
                current_text = result.processed_text

        # All guards passed
        return PipelineResult(
            passed=True,
            original_text=text,
            processed_text=current_text,
            results=results,
            blocked_by=None,
        )

    @property
    def input_guardrails(self) -> list[str]:
        """Get list of input guardrail types."""
        return [g.guardrail_type for g in self._input_guards]

    @property
    def output_guardrails(self) -> list[str]:
        """Get list of output guardrail types."""
        return [g.guardrail_type for g in self._output_guards]


def create_executor_from_config(config: dict) -> GuardrailsExecutor:
    """
    Create executor from guardrails generator output.

    Args:
        config: Output from guardrails generator
                {"guardrails": {"input": [...], "output": [...], "reasoning": "..."}}

    Returns:
        GuardrailsExecutor instance
    """
    guardrails = config.get("guardrails", {})
    return GuardrailsExecutor(
        input_guardrails=guardrails.get("input", []),
        output_guardrails=guardrails.get("output", []),
    )
