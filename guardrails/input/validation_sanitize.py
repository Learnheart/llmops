"""Validation & Sanitization guardrail implementation."""

import re
import html
from typing import Any

from guardrails.base import BaseGuardrail
from schema.guardrails import GuardrailResult, GuardrailAction


class ValidationSanitizeGuardrail(BaseGuardrail):
    """Validate and sanitize user input."""

    @property
    def name(self) -> str:
        return "Validation & Sanitize"

    @property
    def guardrail_type(self) -> str:
        return "validation_sanitize"

    @property
    def default_config(self) -> dict[str, Any]:
        return {
            "max_length": 4096,
            "min_length": 1,
            "strip_whitespace": True,
            "remove_html_tags": True,
            "normalize_unicode": True,
            "blocked_patterns": ["<script>", "javascript:"],
            "enabled": True,
        }

    def check(self, text: str) -> GuardrailResult:
        """Validate and sanitize input text."""
        if not self.config.get("enabled", True):
            return self._pass_result(text, "Validation disabled")

        processed = text
        issues = []

        # Strip whitespace
        if self.config.get("strip_whitespace", True):
            processed = processed.strip()

        # Check min length
        min_length = self.config.get("min_length", 1)
        if len(processed) < min_length:
            return self._fail_result(
                text=text,
                action=GuardrailAction.REJECT,
                message=f"Input too short (min: {min_length})",
                details={"length": len(processed), "min_length": min_length},
            )

        # Check max length
        max_length = self.config.get("max_length", 4096)
        if len(processed) > max_length:
            processed = processed[:max_length]
            issues.append(f"truncated to {max_length} chars")

        # Remove HTML tags
        if self.config.get("remove_html_tags", True):
            original_len = len(processed)
            processed = re.sub(r"<[^>]+>", "", processed)
            processed = html.unescape(processed)
            if len(processed) != original_len:
                issues.append("HTML tags removed")

        # Check blocked patterns
        blocked = self.config.get("blocked_patterns", [])
        for pattern in blocked:
            if pattern.lower() in processed.lower():
                return self._fail_result(
                    text=text,
                    action=GuardrailAction.REJECT,
                    message=f"Blocked pattern detected: {pattern}",
                    details={"blocked_pattern": pattern},
                )

        # Normalize unicode (remove control characters)
        if self.config.get("normalize_unicode", True):
            original = processed
            # Remove control characters except newlines and tabs
            processed = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", processed)
            if processed != original:
                issues.append("control characters removed")

        # Return result
        if issues:
            return self._fail_result(
                text=text,
                action=GuardrailAction.SANITIZE,
                message=f"Input sanitized: {', '.join(issues)}",
                processed_text=processed,
                details={"issues": issues},
            )

        return self._pass_result(processed, "Input validation passed")
