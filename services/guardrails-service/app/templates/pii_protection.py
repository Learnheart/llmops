"""
PII Protection Guardrail Strategy.
Prevents leakage of Personally Identifiable Information.
"""

from app.templates.base import GuardrailStrategy


class PIIProtectionStrategy(GuardrailStrategy):
    """
    Guardrail to protect Personally Identifiable Information (PII).
    """

    name = "pii_protection"
    description = "Prevents exposure or leakage of personally identifiable information"

    def build_guardrail(self, user_context: str, **kwargs) -> str:
        """
        Build PII protection guardrail.

        Args:
            user_context: Description of data types being handled
            **kwargs: Additional parameters (pii_types, redaction_strategy)
        """
        pii_types = kwargs.get(
            "pii_types",
            [
                "names",
                "email_addresses",
                "phone_numbers",
                "addresses",
                "social_security_numbers",
                "credit_card_numbers",
            ],
        )
        redaction_strategy = kwargs.get("redaction_strategy", "mask")

        return f"""# PII Protection Guardrail

## Context
{user_context}

## Protected Information Types
The following types of personally identifiable information (PII) must be protected:
{chr(10).join([f"- {pii_type.replace('_', ' ').title()}" for pii_type in pii_types])}

## Redaction Strategy: {redaction_strategy.upper()}

### Handling Guidelines

1. **Detection**: Actively identify PII in user inputs and generated outputs
2. **Redaction Strategy**: {redaction_strategy}
   - `mask`: Replace PII with masked values (e.g., "***-**-1234")
   - `remove`: Completely remove PII from responses
   - `generalize`: Replace with generic placeholders (e.g., "[NAME]", "[EMAIL]")

3. **Never Include in Responses**:
   - Full names when partial reference suffices
   - Complete email addresses (use [EMAIL] or masked version)
   - Phone numbers (use [PHONE] or masked format)
   - Physical addresses (use city/state only if needed)
   - Government ID numbers (SSN, passport, etc.)
   - Financial account numbers
   - Biometric data
   - Login credentials

4. **Safe Alternatives**:
   - Use anonymous identifiers (User A, Customer 1)
   - Reference roles instead of names (e.g., "the manager")
   - Use generic examples that don't expose real data
   - Aggregate data when possible

## Response Validation Checklist
Before generating any response, verify:
- [ ] No full names are exposed unnecessarily
- [ ] No email addresses are displayed in full
- [ ] No phone numbers are revealed
- [ ] No addresses are included
- [ ] No government IDs or financial account numbers
- [ ] No passwords or credentials
- [ ] PII in examples has been anonymized

## Handling User Requests for PII
- If user asks to include PII: Politely decline and explain privacy concerns
- Offer to use anonymized or masked alternatives
- Suggest using secure channels for sensitive information
- Never generate synthetic PII that could be confused with real data

## Emergency Override
Only include PII if:
1. Explicitly required for the task AND
2. User has confirmed they have authorization AND
3. The context is clearly internal/authorized use

In all cases, add a warning about handling sensitive information responsibly.
"""

    def get_parameters(self):
        return {
            "pii_types": {
                "type": "array",
                "items": {"type": "string"},
                "default": [
                    "names",
                    "email_addresses",
                    "phone_numbers",
                    "addresses",
                    "social_security_numbers",
                    "credit_card_numbers",
                ],
                "description": "Types of PII to protect",
            },
            "redaction_strategy": {
                "type": "string",
                "enum": ["mask", "remove", "generalize"],
                "default": "mask",
                "description": "How to handle detected PII",
            },
        }
