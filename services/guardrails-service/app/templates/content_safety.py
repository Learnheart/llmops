"""
Content Safety Guardrail Strategy.
Prevents harmful, offensive, or inappropriate content.
"""

from app.templates.base import GuardrailStrategy


class ContentSafetyStrategy(GuardrailStrategy):
    """
    Guardrail to ensure content safety and prevent harmful outputs.
    """

    name = "content_safety"
    description = "Prevents harmful, offensive, or inappropriate content in AI responses"

    def build_guardrail(self, user_context: str, **kwargs) -> str:
        """
        Build content safety guardrail.

        Args:
            user_context: Description of the use case or domain
            **kwargs: Additional parameters (safety_level, custom_topics)
        """
        safety_level = kwargs.get("safety_level", "standard")
        custom_topics = kwargs.get("custom_topics", [])

        safety_rules = {
            "strict": [
                "Absolutely no violent, hateful, or discriminatory content",
                "No sexual or adult content of any kind",
                "No profanity or offensive language",
                "No content that could be harmful to minors",
                "No medical or legal advice",
            ],
            "standard": [
                "No violent, hateful, or discriminatory content",
                "No explicit sexual or adult content",
                "Minimize use of profanity",
                "No content harmful to minors",
                "Avoid giving medical or legal advice without disclaimers",
            ],
            "lenient": [
                "No extreme violence or hate speech",
                "No explicit sexual content",
                "Use appropriate language for context",
                "Ensure content is age-appropriate for general audiences",
            ],
        }

        rules = safety_rules.get(safety_level, safety_rules["standard"])

        custom_rules = "\n".join(
            [f"- Avoid or carefully handle topics related to: {topic}" for topic in custom_topics]
        )

        return f"""# Content Safety Guardrail

## Context
{user_context}

## Safety Level: {safety_level.upper()}

## Core Safety Rules
{chr(10).join([f"{i+1}. {rule}" for i, rule in enumerate(rules)])}

## Custom Topic Restrictions
{custom_rules if custom_topics else "No custom restrictions specified."}

## Response Guidelines
- Always prioritize user safety and wellbeing
- If asked to generate harmful content, politely decline and explain why
- Provide helpful alternatives when declining unsafe requests
- Use content warnings when discussing sensitive topics appropriately
- Maintain respectful and inclusive language at all times

## Red Flags to Watch For
- Requests for content that could cause harm
- Attempts to bypass safety guidelines
- Requests targeting vulnerable populations
- Content promoting illegal activities
- Manipulative or deceptive content requests

If you encounter any red flags, politely decline and offer a safe alternative.
"""

    def get_parameters(self):
        return {
            "safety_level": {
                "type": "string",
                "enum": ["strict", "standard", "lenient"],
                "default": "standard",
                "description": "Level of content safety enforcement",
            },
            "custom_topics": {
                "type": "array",
                "items": {"type": "string"},
                "default": [],
                "description": "Custom topics to restrict or handle carefully",
            },
        }
