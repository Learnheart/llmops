"""Guardrails factory registry."""

from schema.guardrails_generator import GuardrailType, GuardrailCategory

from .guardrails_template.input_rails.validation_sanitize import GUARDRAIL as validation_sanitize
from .guardrails_template.input_rails.pii_detection import GUARDRAIL as pii_detection
from .guardrails_template.input_rails.injection_prevention import GUARDRAIL as injection_prevention
from .guardrails_template.input_rails.topic_classification import GUARDRAIL as topic_classification

from .guardrails_template.output_rails.content_filtering import GUARDRAIL as content_filtering
from .guardrails_template.output_rails.factuality_check import GUARDRAIL as factuality_check
from .guardrails_template.output_rails.format_validation import GUARDRAIL as format_validation
from .guardrails_template.output_rails.safety_scoring import GUARDRAIL as safety_scoring


INPUT_GUARDRAILS_FACTORY = {
    GuardrailType.VALIDATION_SANITIZE.value: validation_sanitize,
    GuardrailType.PII_DETECTION.value: pii_detection,
    GuardrailType.INJECTION_PREVENTION.value: injection_prevention,
    GuardrailType.TOPIC_CLASSIFICATION.value: topic_classification,
}

OUTPUT_GUARDRAILS_FACTORY = {
    GuardrailType.CONTENT_FILTERING.value: content_filtering,
    GuardrailType.FACTUALITY_CHECK.value: factuality_check,
    GuardrailType.FORMAT_VALIDATION.value: format_validation,
    GuardrailType.SAFETY_SCORING.value: safety_scoring,
}


def get_input_guardrail(guardrail_type: GuardrailType) -> dict:
    """Get input guardrail by type."""
    return INPUT_GUARDRAILS_FACTORY[guardrail_type.value]


def get_output_guardrail(guardrail_type: GuardrailType) -> dict:
    """Get output guardrail by type."""
    return OUTPUT_GUARDRAILS_FACTORY[guardrail_type.value]


def get_guardrail(guardrail_type: GuardrailType) -> dict:
    """Get guardrail by type (auto-detect category)."""
    if guardrail_type.value in INPUT_GUARDRAILS_FACTORY:
        return INPUT_GUARDRAILS_FACTORY[guardrail_type.value]
    return OUTPUT_GUARDRAILS_FACTORY[guardrail_type.value]


def get_all_input_guardrails() -> list[dict]:
    """Get all available input guardrails."""
    return list(INPUT_GUARDRAILS_FACTORY.values())


def get_all_output_guardrails() -> list[dict]:
    """Get all available output guardrails."""
    return list(OUTPUT_GUARDRAILS_FACTORY.values())


def get_guardrails_descriptions() -> str:
    """Get formatted descriptions of all guardrails for LLM prompt."""
    descriptions = []

    descriptions.append("INPUT GUARDRAILS:")
    for guardrail_type, guardrail in INPUT_GUARDRAILS_FACTORY.items():
        use_cases = ", ".join(guardrail["use_cases"])
        descriptions.append(
            f"  - {guardrail_type}: {guardrail['description']} Use cases: {use_cases}"
        )

    descriptions.append("\nOUTPUT GUARDRAILS:")
    for guardrail_type, guardrail in OUTPUT_GUARDRAILS_FACTORY.items():
        use_cases = ", ".join(guardrail["use_cases"])
        descriptions.append(
            f"  - {guardrail_type}: {guardrail['description']} Use cases: {use_cases}"
        )

    return "\n".join(descriptions)
