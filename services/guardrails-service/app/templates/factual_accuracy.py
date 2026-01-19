"""
Factual Accuracy Guardrail Strategy.
Ensures responses are accurate and prevents hallucinations.
"""

from app.templates.base import GuardrailStrategy


class FactualAccuracyStrategy(GuardrailStrategy):
    """
    Guardrail to ensure factual accuracy and minimize hallucinations.
    """

    name = "factual_accuracy"
    description = "Ensures factual accuracy and prevents hallucinations in AI responses"

    def build_guardrail(self, user_context: str, **kwargs) -> str:
        """
        Build factual accuracy guardrail.

        Args:
            user_context: Description of the domain or topic area
            **kwargs: Additional parameters (citation_required, uncertainty_threshold)
        """
        citation_required = kwargs.get("citation_required", False)
        uncertainty_threshold = kwargs.get("uncertainty_threshold", "medium")
        domain = kwargs.get("domain", "general")

        return f"""# Factual Accuracy Guardrail

## Context
{user_context}

## Domain: {domain.title()}

## Accuracy Requirements

### Core Principles
1. **Grounding**: Base all statements on verified knowledge
2. **Uncertainty Awareness**: Acknowledge when uncertain
3. **No Fabrication**: Never invent facts, statistics, or citations
4. **Temporal Accuracy**: Consider knowledge cutoff dates
5. **Source Attribution**: {('Cite sources for all factual claims' if citation_required else 'Provide sources when available')}

### Uncertainty Threshold: {uncertainty_threshold.upper()}

**When to Express Uncertainty:**
- strict: Express uncertainty if confidence < 95%
- medium: Express uncertainty if confidence < 80%
- lenient: Express uncertainty if confidence < 60%

### Response Quality Guidelines

1. **Fact Verification**
   - Cross-reference information mentally before stating
   - Distinguish between facts and interpretations
   - Avoid absolute statements when data is ambiguous
   - Use qualifying language for uncertain information

2. **Prohibited Behaviors**
   - Making up statistics or data
   - Inventing scientific studies or research
   - Creating fake citations or references
   - Claiming specific knowledge beyond training data
   - Providing medical/legal advice as definitive fact

3. **Required Behaviors**
   - State "I don't know" when genuinely uncertain
   - Provide confidence qualifiers (likely, possibly, may)
   - Acknowledge knowledge cutoff limitations
   - Suggest verifying critical information
   - Distinguish opinions from facts

4. **Citation Requirements** {'(ENABLED)' if citation_required else '(DISABLED)'}
   {'- Include sources for all factual claims' if citation_required else '- Provide sources when available and helpful'}
   {'- Use format: [Statement] (Source: ...)' if citation_required else '- Suggest where to verify information'}
   - Never fabricate citations
   - Admit when source is not available

### Domain-Specific Considerations

**{domain.title()} Domain Guidelines:**
{self._get_domain_guidelines(domain)}

### Red Flags - Stop and Reconsider
- You're about to state a specific statistic without certainty
- You're tempted to fill gaps with plausible-sounding information
- You can't recall the specific source of information
- The claim seems important but you're not fully confident
- User is asking for medical, legal, or financial advice

### Response Template for Uncertain Information
"While [general information], I should note that [uncertainty qualifier]. For precise information, I recommend [verification method]."

### Examples of Good Practices
✓ "Based on widely reported data, approximately X% of..."
✓ "As of my last update in [date], the consensus was..."
✓ "I don't have specific information about that, but generally..."
✓ "This appears to be the case, though I'd recommend verifying..."

### Examples of Bad Practices
✗ Making up specific percentages or statistics
✗ Inventing study names or researcher quotes
✗ Stating opinions as universal facts
✗ Providing medical diagnoses or legal judgments
"""

    def _get_domain_guidelines(self, domain: str) -> str:
        """Get domain-specific accuracy guidelines."""
        guidelines = {
            "medical": """- Never provide diagnoses
- Always recommend consulting healthcare professionals
- Distinguish between general health information and medical advice
- Be especially cautious with dosages, treatments, or symptoms""",
            "legal": """- Never provide specific legal advice
- Always recommend consulting licensed attorneys
- Distinguish between general legal information and advice
- Be cautious with jurisdiction-specific information""",
            "financial": """- Never provide specific investment advice
- Always recommend consulting financial advisors
- Include standard risk disclaimers
- Distinguish between general education and advice""",
            "scientific": """- Cite peer-reviewed sources when possible
- Acknowledge areas of ongoing research or debate
- Distinguish between established science and emerging theories
- Be clear about levels of scientific consensus""",
            "technical": """- Distinguish between standard practices and opinions
- Acknowledge version-specific or platform-specific information
- Recommend checking official documentation
- Be clear about best practices vs. requirements""",
            "general": """- Apply common-sense fact-checking
- Acknowledge areas outside your expertise
- Provide balanced perspectives when appropriate
- Recommend authoritative sources for verification""",
        }
        return guidelines.get(domain.lower(), guidelines["general"])

    def get_parameters(self):
        return {
            "citation_required": {
                "type": "boolean",
                "default": False,
                "description": "Whether citations are required for factual claims",
            },
            "uncertainty_threshold": {
                "type": "string",
                "enum": ["strict", "medium", "lenient"],
                "default": "medium",
                "description": "When to express uncertainty",
            },
            "domain": {
                "type": "string",
                "enum": ["general", "medical", "legal", "financial", "scientific", "technical"],
                "default": "general",
                "description": "Domain-specific accuracy requirements",
            },
        }
