"""Pydantic models for Guardrails Generator module."""

from enum import Enum
from pydantic import BaseModel


class GuardrailType(str, Enum):
    """Supported guardrail types."""
    # Input guardrails
    VALIDATION_SANITIZE = "validation_sanitize"
    PII_DETECTION = "pii_detection"
    INJECTION_PREVENTION = "injection_prevention"
    TOPIC_CLASSIFICATION = "topic_classification"
    # Output guardrails
    CONTENT_FILTERING = "content_filtering"
    FACTUALITY_CHECK = "factuality_check"
    FORMAT_VALIDATION = "format_validation"
    SAFETY_SCORING = "safety_scoring"


class GuardrailCategory(str, Enum):
    """Guardrail category."""
    INPUT = "input"
    OUTPUT = "output"


class GuardrailInfo(BaseModel):
    """Guardrail metadata and default config."""
    type: GuardrailType
    category: GuardrailCategory
    name: str
    description: str
    default_config: dict


class AnalysisResult(BaseModel):
    """Result from LLM analysis of agent description."""
    input_guardrails: list[GuardrailType]
    output_guardrails: list[GuardrailType]
    reasoning: str
    risk_factors: list[str]
    domain: str
    sensitivity_level: str  # low, medium, high


class GeneratedGuardrail(BaseModel):
    """A generated guardrail config."""
    type: GuardrailType
    category: GuardrailCategory
    name: str
    config: dict
    priority: int


class GuardrailsGeneratorInput(BaseModel):
    """Input for guardrails generator."""
    agent_description: str


class GuardrailsGeneratorOutput(BaseModel):
    """Output from guardrails generator."""
    analysis: AnalysisResult
    input_guardrails: list[GeneratedGuardrail]
    output_guardrails: list[GeneratedGuardrail]
