"""Format Validation guardrail implementation."""

import json
from typing import Any

from guardrails.base import BaseGuardrail
from schema.guardrails import GuardrailResult, GuardrailAction


class FormatValidationGuardrail(BaseGuardrail):
    """Validate output format and structure."""

    @property
    def name(self) -> str:
        return "Format Validation"

    @property
    def guardrail_type(self) -> str:
        return "format_validation"

    @property
    def default_config(self) -> dict[str, Any]:
        return {
            "expected_format": "text",  # text | json | markdown
            "max_length": 4096,
            "min_length": 1,
            "json_schema": None,  # JSON schema for validation
            "required_fields": [],  # For JSON format
            "forbidden_patterns": [],
            "enabled": True,
        }

    def check(self, text: str) -> GuardrailResult:
        """Validate output format."""
        if not self.config.get("enabled", True):
            return self._pass_result(text, "Format validation disabled")

        issues = []

        # Check length
        min_length = self.config.get("min_length", 1)
        max_length = self.config.get("max_length", 4096)

        if len(text) < min_length:
            return self._fail_result(
                text=text,
                action=GuardrailAction.REJECT,
                message=f"Output too short (min: {min_length})",
                details={"length": len(text), "min_length": min_length},
            )

        processed = text
        if len(text) > max_length:
            processed = text[:max_length]
            issues.append(f"truncated to {max_length} chars")

        # Check forbidden patterns
        for pattern in self.config.get("forbidden_patterns", []):
            if pattern in text:
                return self._fail_result(
                    text=text,
                    action=GuardrailAction.REJECT,
                    message=f"Forbidden pattern in output: {pattern}",
                    details={"forbidden_pattern": pattern},
                )

        # Format-specific validation
        expected_format = self.config.get("expected_format", "text")

        if expected_format == "json":
            json_result = self._validate_json(text)
            if not json_result["valid"]:
                return self._fail_result(
                    text=text,
                    action=GuardrailAction.REJECT,
                    message=f"Invalid JSON: {json_result['error']}",
                    details=json_result,
                )

        # Return result
        if issues:
            return self._fail_result(
                text=text,
                action=GuardrailAction.SANITIZE,
                message=f"Output adjusted: {', '.join(issues)}",
                processed_text=processed,
                details={"issues": issues},
            )

        return self._pass_result(text, "Format validation passed")

    def _validate_json(self, text: str) -> dict:
        """Validate JSON format and required fields."""
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            return {"valid": False, "error": str(e)}

        # Check required fields
        required_fields = self.config.get("required_fields", [])
        if required_fields and isinstance(data, dict):
            missing = [f for f in required_fields if f not in data]
            if missing:
                return {"valid": False, "error": f"Missing fields: {missing}"}

        return {"valid": True, "parsed": data}
