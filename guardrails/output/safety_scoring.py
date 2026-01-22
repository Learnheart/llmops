"""Safety Scoring guardrail implementation."""

import re
from typing import Any

from guardrails.base import BaseGuardrail
from schema.guardrails import GuardrailResult, GuardrailAction


class SafetyScoringGuardrail(BaseGuardrail):
    """Score output safety across multiple dimensions."""

    # Keywords for scoring (simplified - in production use ML model)
    SCORING_KEYWORDS = {
        "toxicity": {
            "high": ["hate", "kill", "murder", "die", "stupid", "idiot", "moron"],
            "medium": ["dumb", "annoying", "terrible", "awful", "worst"],
            "low": ["bad", "wrong", "disagree"],
        },
        "bias": {
            "high": ["always", "never", "all X are", "no X can"],
            "medium": ["typically", "usually", "most X are"],
            "low": ["sometimes", "often"],
        },
        "harmful_advice": {
            "high": ["you should harm", "try killing", "don't seek help"],
            "medium": ["skip the doctor", "ignore symptoms"],
            "low": ["might not need"],
        },
    }

    @property
    def name(self) -> str:
        return "Safety Scoring"

    @property
    def guardrail_type(self) -> str:
        return "safety_scoring"

    @property
    def default_config(self) -> dict[str, Any]:
        return {
            "scoring_dimensions": ["toxicity", "bias", "harmful_advice"],
            "thresholds": {
                "toxicity": 0.3,
                "bias": 0.4,
                "harmful_advice": 0.2,
            },
            "action": "reject",  # reject | warn
            "enabled": True,
        }

    def check(self, text: str) -> GuardrailResult:
        """Score output safety."""
        if not self.config.get("enabled", True):
            return self._pass_result(text, "Safety scoring disabled")

        dimensions = self.config.get("scoring_dimensions", [])
        thresholds = self.config.get("thresholds", {})
        action = self.config.get("action", "reject")

        scores = {}
        violations = []

        text_lower = text.lower()

        # Calculate scores for each dimension
        for dimension in dimensions:
            score = self._calculate_score(text_lower, dimension)
            scores[dimension] = score

            threshold = thresholds.get(dimension, 0.5)
            if score > threshold:
                violations.append({
                    "dimension": dimension,
                    "score": score,
                    "threshold": threshold,
                })

        # No violations
        if not violations:
            return self._pass_result(
                text,
                f"Safety check passed. Scores: {scores}"
            )

        # Take action
        if action == "warn":
            return self._fail_result(
                text=text,
                action=GuardrailAction.WARN,
                message=f"Safety warning: {[v['dimension'] for v in violations]}",
                processed_text=text,
                details={"scores": scores, "violations": violations},
            )

        return self._fail_result(
            text=text,
            action=GuardrailAction.REJECT,
            message=f"Safety threshold exceeded: {[v['dimension'] for v in violations]}",
            details={"scores": scores, "violations": violations},
        )

    def _calculate_score(self, text: str, dimension: str) -> float:
        """
        Calculate safety score for a dimension (0.0 = safe, 1.0 = unsafe).

        Note: This is a simplified keyword-based approach.
        In production, use ML models like Perspective API or custom classifiers.
        """
        keywords = self.SCORING_KEYWORDS.get(dimension, {})

        score = 0.0
        matches = {"high": 0, "medium": 0, "low": 0}

        for severity, words in keywords.items():
            for word in words:
                if re.search(r"\b" + re.escape(word.lower()) + r"\b", text):
                    matches[severity] += 1

        # Weight by severity
        score = (
            matches["high"] * 0.4 +
            matches["medium"] * 0.2 +
            matches["low"] * 0.05
        )

        # Normalize to 0-1 range (cap at 1.0)
        return min(score, 1.0)
