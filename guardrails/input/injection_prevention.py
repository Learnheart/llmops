"""Injection Prevention guardrail implementation."""

import re
from typing import Any

from guardrails.base import BaseGuardrail
from schema.guardrails import GuardrailResult, GuardrailAction


class InjectionPreventionGuardrail(BaseGuardrail):
    """Detect and prevent prompt injection and jailbreak attempts."""

    # Common injection patterns
    INJECTION_PATTERNS = {
        "prompt_injection": [
            r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?)",
            r"disregard\s+(all\s+)?(previous|above|prior)",
            r"forget\s+(everything|all|your)\s+(instructions?|rules?|guidelines?)",
            r"new\s+instructions?:",
            r"system\s*prompt:",
        ],
        "jailbreak": [
            r"DAN\s+mode",
            r"developer\s+mode",
            r"jailbreak",
            r"bypass\s+(safety|filter|restriction)",
            r"pretend\s+you\s+(have\s+)?no\s+(restrictions?|limitations?|rules?)",
        ],
        "role_escape": [
            r"you\s+are\s+now\s+(?!going\s+to\s+help)",
            r"act\s+as\s+(if\s+you\s+are|a)",
            r"pretend\s+(to\s+be|you\s+are)",
            r"roleplay\s+as",
            r"from\s+now\s+on\s+you\s+are",
        ],
        "instruction_override": [
            r"\[system\]",
            r"\[admin\]",
            r"\[override\]",
            r"</?(system|assistant|user)>",
            r"###\s*(instruction|system|prompt)",
        ],
        "delimiter_attack": [
            r"```\s*(system|instruction|prompt)",
            r"---+\s*(system|new\s+instruction)",
            r"={3,}",
        ],
    }

    @property
    def name(self) -> str:
        return "Injection Prevention"

    @property
    def guardrail_type(self) -> str:
        return "injection_prevention"

    @property
    def default_config(self) -> dict[str, Any]:
        return {
            "detect_types": [
                "prompt_injection",
                "jailbreak",
                "role_escape",
                "instruction_override",
            ],
            "action": "reject",  # reject | warn | sanitize
            "sensitivity": "medium",  # low | medium | high
            "custom_patterns": [],
            "enabled": True,
        }

    def check(self, text: str) -> GuardrailResult:
        """Check for injection attempts."""
        if not self.config.get("enabled", True):
            return self._pass_result(text, "Injection prevention disabled")

        detect_types = self.config.get("detect_types", [])
        action = self.config.get("action", "reject")
        detected = {}

        # Check each injection type
        for injection_type in detect_types:
            patterns = self.INJECTION_PATTERNS.get(injection_type, [])
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    if injection_type not in detected:
                        detected[injection_type] = []
                    detected[injection_type].append(pattern)

        # Check custom patterns
        for pattern in self.config.get("custom_patterns", []):
            if re.search(pattern, text, re.IGNORECASE):
                if "custom" not in detected:
                    detected["custom"] = []
                detected["custom"].append(pattern)

        # No injection detected
        if not detected:
            return self._pass_result(text, "No injection attempts detected")

        # Take action
        if action == "reject":
            return self._fail_result(
                text=text,
                action=GuardrailAction.REJECT,
                message=f"Potential injection detected: {list(detected.keys())}",
                details={"detected_types": detected},
            )

        if action == "warn":
            return self._fail_result(
                text=text,
                action=GuardrailAction.WARN,
                message=f"Warning: Potential injection: {list(detected.keys())}",
                processed_text=text,
                details={"detected_types": detected},
            )

        # Sanitize: remove detected patterns
        sanitized = self._sanitize(text, detected)
        return self._fail_result(
            text=text,
            action=GuardrailAction.SANITIZE,
            message=f"Injection patterns sanitized: {list(detected.keys())}",
            processed_text=sanitized,
            details={"detected_types": detected},
        )

    def _sanitize(self, text: str, detected: dict) -> str:
        """Remove detected injection patterns from text."""
        sanitized = text
        for patterns in detected.values():
            for pattern in patterns:
                sanitized = re.sub(pattern, "[REMOVED]", sanitized, flags=re.IGNORECASE)
        return sanitized
