"""Pydantic models for Guardrails runtime module."""

from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel


class GuardrailAction(str, Enum):
    """Action to take when guardrail is triggered."""
    PASS = "pass"           # Allow through
    MASK = "mask"           # Mask sensitive content
    REJECT = "reject"       # Block entirely
    WARN = "warn"           # Allow but flag
    SANITIZE = "sanitize"   # Clean and allow


class GuardrailResult(BaseModel):
    """Result from a guardrail check."""
    passed: bool                        # True if check passed
    action_taken: GuardrailAction       # What action was applied
    original_text: str                  # Original input
    processed_text: Optional[str]       # Modified text (if any)
    message: str                        # Human-readable result
    details: dict[str, Any] = {}        # Additional info (matches found, scores, etc.)


class GuardrailConfig(BaseModel):
    """Configuration for a guardrail."""
    type: str                           # Guardrail type name
    enabled: bool = True
    config: dict[str, Any] = {}         # Type-specific config


class GuardrailsPipelineConfig(BaseModel):
    """Configuration for guardrails pipeline."""
    input_guardrails: list[GuardrailConfig] = []
    output_guardrails: list[GuardrailConfig] = []


class PipelineResult(BaseModel):
    """Result from running full guardrails pipeline."""
    passed: bool                        # Overall pass/fail
    original_text: str
    processed_text: str                 # Final processed text
    results: list[GuardrailResult]      # Individual guardrail results
    blocked_by: Optional[str] = None    # Which guardrail blocked (if any)
