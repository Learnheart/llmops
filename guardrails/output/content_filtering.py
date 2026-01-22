"""Content Filtering guardrail implementation."""

import re
from typing import Any

from guardrails.base import BaseGuardrail
from schema.guardrails import GuardrailResult, GuardrailAction


class ContentFilteringGuardrail(BaseGuardrail):
    """Filter inappropriate content from model output."""

    # Content patterns to filter
    CONTENT_PATTERNS = {
        "profanity": [
            r"\b(fuck|shit|damn|ass|bitch|bastard)\b",
        ],
        "hate_speech": [
            r"\b(hate|kill all|exterminate|inferior race)\b",
        ],
        "violence": [
            r"\b(murder|torture|mutilate|slaughter)\b",
            r"how to (kill|harm|hurt|attack)",
        ],
        "illegal_advice": [
            r"how to (hack|steal|fraud|smuggle)",
            r"step.?by.?step.*(illegal|crime|hack)",
        ],
    }

    @property
    def name(self) -> str:
        return "Content Filtering"

    @property
    def guardrail_type(self) -> str:
        return "content_filtering"

    @property
    def default_config(self) -> dict[str, Any]:
        return {
            "filter_categories": ["profanity", "hate_speech", "violence", "illegal_advice"],
            "action": "redact",  # redact | reject | warn
            "replacement_text": "[Content removed]",
            "sensitivity": "medium",  # low | medium | high
            "custom_filters": [],
            "enabled": True,
        }

    def check(self, text: str) -> GuardrailResult:
        """Filter inappropriate content from output."""
        if not self.config.get("enabled", True):
            return self._pass_result(text, "Content filtering disabled")

        filter_categories = self.config.get("filter_categories", [])
        action = self.config.get("action", "redact")
        found_content = {}

        # Check each category
        for category in filter_categories:
            patterns = self.CONTENT_PATTERNS.get(category, [])
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    if category not in found_content:
                        found_content[category] = []
                    found_content[category].extend(matches)

        # Check custom filters
        for pattern in self.config.get("custom_filters", []):
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                if "custom" not in found_content:
                    found_content["custom"] = []
                found_content["custom"].extend(matches)

        # No issues found
        if not found_content:
            return self._pass_result(text, "Content check passed")

        # Take action
        if action == "reject":
            return self._fail_result(
                text=text,
                action=GuardrailAction.REJECT,
                message=f"Inappropriate content detected: {list(found_content.keys())}",
                details={"found_content": found_content},
            )

        if action == "warn":
            return self._fail_result(
                text=text,
                action=GuardrailAction.WARN,
                message=f"Warning: Content flagged: {list(found_content.keys())}",
                processed_text=text,
                details={"found_content": found_content},
            )

        # Redact
        replacement = self.config.get("replacement_text", "[Content removed]")
        redacted = self._redact_content(text, found_content, replacement)
        return self._fail_result(
            text=text,
            action=GuardrailAction.SANITIZE,
            message=f"Content redacted: {list(found_content.keys())}",
            processed_text=redacted,
            details={"found_content": found_content},
        )

    def _redact_content(self, text: str, found_content: dict, replacement: str) -> str:
        """Redact found content from text."""
        redacted = text
        for matches in found_content.values():
            for match in matches:
                if isinstance(match, str):
                    redacted = re.sub(
                        re.escape(match), replacement, redacted, flags=re.IGNORECASE
                    )
        return redacted
