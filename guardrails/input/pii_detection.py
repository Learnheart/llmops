"""PII Detection guardrail implementation."""

import re
from typing import Any

from guardrails.base import BaseGuardrail
from schema.guardrails import GuardrailResult, GuardrailAction


class PIIDetectionGuardrail(BaseGuardrail):
    """Detect and mask personally identifiable information."""

    # Regex patterns for common PII types
    PII_PATTERNS = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"\b(?:\+?84|0)(?:\d{9,10}|\d{3}[-.\s]?\d{3}[-.\s]?\d{4})\b",
        "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
        "ssn": r"\b\d{3}[-]?\d{2}[-]?\d{4}\b",
        "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "date_of_birth": r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{2,4}[/-]\d{1,2}[/-]\d{1,2})\b",
    }

    @property
    def name(self) -> str:
        return "PII Detection & Masking"

    @property
    def guardrail_type(self) -> str:
        return "pii_detection"

    @property
    def default_config(self) -> dict[str, Any]:
        return {
            "detect_types": ["email", "phone", "credit_card"],
            "action": "mask",  # mask | reject | warn
            "mask_char": "*",
            "mask_preserve_length": True,
            "custom_patterns": {},
            "enabled": True,
        }

    def check(self, text: str) -> GuardrailResult:
        """Detect PII in text and take configured action."""
        if not self.config.get("enabled", True):
            return self._pass_result(text, "PII detection disabled")

        detect_types = self.config.get("detect_types", [])
        action = self.config.get("action", "mask")
        found_pii = {}

        # Check each PII type
        for pii_type in detect_types:
            pattern = self.PII_PATTERNS.get(pii_type)
            if pattern:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    found_pii[pii_type] = matches

        # Check custom patterns
        for name, pattern in self.config.get("custom_patterns", {}).items():
            matches = re.findall(pattern, text)
            if matches:
                found_pii[name] = matches

        # No PII found
        if not found_pii:
            return self._pass_result(text, "No PII detected")

        # Take action based on config
        if action == "reject":
            return self._fail_result(
                text=text,
                action=GuardrailAction.REJECT,
                message=f"PII detected: {list(found_pii.keys())}",
                details={"found_pii": found_pii},
            )

        if action == "warn":
            return self._fail_result(
                text=text,
                action=GuardrailAction.WARN,
                message=f"Warning: PII detected: {list(found_pii.keys())}",
                processed_text=text,
                details={"found_pii": found_pii},
            )

        # Default: mask
        masked_text = self._mask_pii(text, found_pii)
        return self._fail_result(
            text=text,
            action=GuardrailAction.MASK,
            message=f"PII masked: {list(found_pii.keys())}",
            processed_text=masked_text,
            details={"found_pii": found_pii},
        )

    def _mask_pii(self, text: str, found_pii: dict) -> str:
        """Mask detected PII in text."""
        mask_char = self.config.get("mask_char", "*")
        preserve_length = self.config.get("mask_preserve_length", True)

        masked = text
        for pii_type, matches in found_pii.items():
            for match in matches:
                if preserve_length:
                    replacement = mask_char * len(match)
                else:
                    replacement = f"[{pii_type.upper()}]"
                masked = masked.replace(match, replacement)

        return masked
