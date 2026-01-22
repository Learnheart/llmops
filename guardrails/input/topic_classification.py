"""Topic Classification guardrail implementation."""

import re
from typing import Any

from guardrails.base import BaseGuardrail
from schema.guardrails import GuardrailResult, GuardrailAction


class TopicClassificationGuardrail(BaseGuardrail):
    """Classify input topic and filter blocked topics."""

    # Simple keyword-based topic detection
    TOPIC_KEYWORDS = {
        "violence": [
            "kill", "murder", "attack", "weapon", "bomb", "hurt", "harm",
            "assault", "fight", "beat", "shoot", "stab",
        ],
        "illegal_activities": [
            "hack", "crack", "steal", "fraud", "illegal", "drug",
            "smuggle", "counterfeit", "pirate", "exploit",
        ],
        "adult_content": [
            "porn", "xxx", "nude", "sex", "explicit", "nsfw",
        ],
        "self_harm": [
            "suicide", "self-harm", "cut myself", "end my life",
            "kill myself", "hurt myself",
        ],
        "hate_speech": [
            "hate", "racist", "sexist", "discriminate", "slur",
        ],
    }

    @property
    def name(self) -> str:
        return "Topic Classification"

    @property
    def guardrail_type(self) -> str:
        return "topic_classification"

    @property
    def default_config(self) -> dict[str, Any]:
        return {
            "blocked_topics": ["violence", "illegal_activities", "adult_content", "self_harm"],
            "allowed_topics": [],  # If set, only these topics allowed
            "action": "reject",  # reject | warn | redirect
            "redirect_message": "I cannot help with that topic.",
            "custom_topics": {},  # {topic_name: [keywords]}
            "enabled": True,
        }

    def check(self, text: str) -> GuardrailResult:
        """Classify topic and check against blocked list."""
        if not self.config.get("enabled", True):
            return self._pass_result(text, "Topic classification disabled")

        text_lower = text.lower()
        detected_topics = []

        # Check built-in topics
        blocked_topics = self.config.get("blocked_topics", [])
        for topic in blocked_topics:
            keywords = self.TOPIC_KEYWORDS.get(topic, [])
            for keyword in keywords:
                if re.search(r"\b" + re.escape(keyword) + r"\b", text_lower):
                    if topic not in detected_topics:
                        detected_topics.append(topic)
                    break

        # Check custom topics
        custom_topics = self.config.get("custom_topics", {})
        for topic, keywords in custom_topics.items():
            if topic in blocked_topics:
                for keyword in keywords:
                    if keyword.lower() in text_lower:
                        if topic not in detected_topics:
                            detected_topics.append(topic)
                        break

        # No blocked topics detected
        if not detected_topics:
            return self._pass_result(text, "Topic check passed")

        # Take action
        action = self.config.get("action", "reject")

        if action == "reject":
            return self._fail_result(
                text=text,
                action=GuardrailAction.REJECT,
                message=f"Blocked topic detected: {detected_topics}",
                details={"detected_topics": detected_topics},
            )

        if action == "warn":
            return self._fail_result(
                text=text,
                action=GuardrailAction.WARN,
                message=f"Warning: Sensitive topic: {detected_topics}",
                processed_text=text,
                details={"detected_topics": detected_topics},
            )

        # Redirect
        redirect_message = self.config.get("redirect_message", "I cannot help with that topic.")
        return self._fail_result(
            text=text,
            action=GuardrailAction.REJECT,
            message=redirect_message,
            details={"detected_topics": detected_topics, "redirected": True},
        )
