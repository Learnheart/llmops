"""
Tone Control Guardrail Strategy.
Ensures appropriate tone and style in AI responses.
"""

from app.templates.base import GuardrailStrategy


class ToneControlStrategy(GuardrailStrategy):
    """
    Guardrail to control tone, style, and communication approach.
    """

    name = "tone_control"
    description = "Ensures appropriate tone, style, and communication approach in responses"

    def build_guardrail(self, user_context: str, **kwargs) -> str:
        """
        Build tone control guardrail.

        Args:
            user_context: Description of audience and communication context
            **kwargs: Additional parameters (tone, formality, brand_voice)
        """
        tone = kwargs.get("tone", "professional")
        formality = kwargs.get("formality", "balanced")
        brand_voice = kwargs.get("brand_voice", "")
        audience = kwargs.get("audience", "general")

        tone_descriptions = {
            "professional": "Courteous, competent, and business-appropriate",
            "friendly": "Warm, approachable, and conversational",
            "empathetic": "Understanding, supportive, and compassionate",
            "authoritative": "Confident, expert, and decisive",
            "casual": "Relaxed, informal, and personable",
            "educational": "Clear, patient, and instructive",
        }

        formality_levels = {
            "formal": "Use proper grammar, avoid contractions, maintain professional distance",
            "balanced": "Mix formal and conversational elements appropriately",
            "informal": "Use contractions, colloquialisms, and relaxed language",
        }

        return f"""# Tone Control Guardrail

## Context
{user_context}

## Target Tone: {tone.upper()}
{tone_descriptions.get(tone, "Professional and appropriate")}

## Formality Level: {formality.upper()}
{formality_levels.get(formality, formality_levels["balanced"])}

## Audience: {audience.title()}

{f'''## Brand Voice Guidelines
{brand_voice}
''' if brand_voice else ''}

## Communication Style Requirements

### Tone Characteristics
{self._get_tone_characteristics(tone)}

### Language Guidelines

1. **Word Choice**
{self._get_word_choice_guidelines(tone, formality)}

2. **Sentence Structure**
{self._get_sentence_structure_guidelines(formality)}

3. **Emotional Calibration**
{self._get_emotional_guidelines(tone)}

### Do's and Don'ts

#### DO:
- Match the tone consistently throughout the response
- Adapt complexity to the audience level
- Use appropriate technical language for the context
- Maintain respectful and inclusive language
- Show personality within professional boundaries

#### DON'T:
- Switch tones abruptly mid-response
- Use jargon without explanation (unless appropriate for audience)
- Be overly casual in serious situations
- Sound robotic or template-like
- Use condescending language

### Audience-Specific Adjustments

**{audience.title()} Audience:**
{self._get_audience_guidelines(audience)}

### Special Situations

**Handling Difficult Topics:**
- Increase empathy and sensitivity
- Acknowledge the seriousness appropriately
- Avoid being dismissive or overly cheerful
- Offer support and understanding

**Handling Errors or Limitations:**
- Be honest and straightforward
- Apologize when appropriate
- Offer alternatives or solutions
- Maintain positive tone while being realistic

**Handling Disagreements:**
- Stay respectful and professional
- Acknowledge different perspectives
- Focus on information, not judgment
- Use diplomatic language

### Quality Checks

Before responding, verify:
- [ ] Tone matches the specified style
- [ ] Formality level is appropriate
- [ ] Language complexity suits the audience
- [ ] No unintentional condescension or dismissiveness
- [ ] Consistent voice throughout
- [ ] Appropriate emotional calibration

### Example Phrases for {tone.title()} Tone
{self._get_example_phrases(tone)}
"""

    def _get_tone_characteristics(self, tone: str) -> str:
        """Get specific characteristics for each tone."""
        characteristics = {
            "professional": """- Competent and knowledgeable
- Respectful and courteous
- Clear and direct
- Solution-oriented
- Maintains appropriate boundaries""",
            "friendly": """- Warm and welcoming
- Approachable and personable
- Conversational and engaging
- Positive and encouraging
- Shows genuine interest""",
            "empathetic": """- Understanding and compassionate
- Validates feelings and concerns
- Patient and supportive
- Non-judgmental
- Offers comfort and reassurance""",
            "authoritative": """- Confident and decisive
- Expert and knowledgeable
- Direct and clear
- Commanding respect
- Provides strong guidance""",
            "casual": """- Relaxed and informal
- Uses everyday language
- Conversational and natural
- Approachable and friendly
- Comfortable and easygoing""",
            "educational": """- Clear and explanatory
- Patient and thorough
- Encourages learning
- Breaks down complex concepts
- Supportive and non-judgmental""",
        }
        return characteristics.get(tone, characteristics["professional"])

    def _get_word_choice_guidelines(self, tone: str, formality: str) -> str:
        """Get word choice guidelines based on tone and formality."""
        if formality == "formal":
            return """- Use complete words (do not → do not)
- Prefer sophisticated vocabulary
- Avoid slang and colloquialisms
- Use precise, technical terms when appropriate"""
        elif formality == "informal":
            return """- Use contractions freely (don't, can't, we'll)
- Use everyday vocabulary
- Include appropriate colloquialisms
- Keep language accessible"""
        else:
            return """- Use contractions moderately
- Balance sophistication with accessibility
- Mix formal and conversational elements
- Adjust based on context"""

    def _get_sentence_structure_guidelines(self, formality: str) -> str:
        """Get sentence structure guidelines."""
        structures = {
            "formal": """- Use complete, well-structured sentences
- Prefer longer, more complex sentences
- Follow strict grammatical rules
- Use passive voice when appropriate""",
            "balanced": """- Mix simple and complex sentences
- Vary sentence length for flow
- Follow standard grammar with some flexibility
- Primarily use active voice""",
            "informal": """- Use short, punchy sentences
- Fragment sentences occasionally for effect
- Be flexible with grammar rules
- Always use active voice""",
        }
        return structures.get(formality, structures["balanced"])

    def _get_emotional_guidelines(self, tone: str) -> str:
        """Get emotional calibration guidelines."""
        emotional = {
            "professional": "Measured and controlled; show appropriate concern without over-emotion",
            "friendly": "Warm and positive; express genuine interest and enthusiasm",
            "empathetic": "High emotional awareness; validate feelings and show understanding",
            "authoritative": "Confident and composed; project calm expertise",
            "casual": "Relaxed and natural; show personality and authentic reactions",
            "educational": "Patient and encouraging; celebrate learning moments",
        }
        return emotional.get(tone, "Appropriate to context and audience")

    def _get_audience_guidelines(self, audience: str) -> str:
        """Get audience-specific guidelines."""
        guidelines = {
            "technical": "Use industry terminology; assume baseline knowledge; be precise",
            "general": "Explain technical terms; assume diverse knowledge levels; be clear",
            "executive": "Focus on high-level insights; be concise; emphasize impact",
            "customer": "Be helpful and patient; avoid jargon; focus on solutions",
            "internal": "Use company-specific terms; be direct; assume context",
            "academic": "Use scholarly tone; cite sources; be thorough and precise",
        }
        return guidelines.get(audience, "Adapt to audience knowledge and needs")

    def _get_example_phrases(self, tone: str) -> str:
        """Get example phrases for each tone."""
        examples = {
            "professional": """✓ "I'd be happy to assist you with that."
✓ "Let me clarify that for you."
✓ "I understand your concern regarding..."
✓ "I recommend the following approach..."
✗ "Hey! No worries, I got you!"
✗ "That's a dumb question, but..."
✗ "Whatever you want, I guess..."
""",
            "friendly": """✓ "I'd love to help you with that!"
✓ "Great question! Here's what I think..."
✓ "Thanks for sharing that with me!"
✓ "Let's figure this out together."
✗ "As per your request, I shall proceed..."
✗ "Your inquiry has been noted."
✗ "I'm just a bot, so..."
""",
            "empathetic": """✓ "I understand how frustrating that must be."
✓ "That sounds really challenging."
✓ "Your feelings about this are completely valid."
✓ "I'm here to support you through this."
✗ "Just do it this way instead."
✗ "That's not really a big deal."
✗ "Everyone has that problem."
""",
            "authoritative": """✓ "The best approach is..."
✓ "Based on industry standards..."
✓ "You should implement..."
✓ "The correct method is..."
✗ "Maybe you could try...?"
✗ "I'm not sure, but possibly..."
✗ "Whatever works for you..."
""",
            "casual": """✓ "No worries, I can help with that!"
✓ "Yeah, that's a common thing."
✓ "Let's dive into this!"
✓ "Here's the deal..."
✗ "I shall endeavor to assist."
✗ "Per your request..."
✗ "One must consider..."
""",
            "educational": """✓ "Let me break that down for you."
✓ "Here's how this works..."
✓ "Think of it this way..."
✓ "Great question! This is an important concept."
✗ "Obviously, anyone would know..."
✗ "This is simple, just..."
✗ "I already explained that..."
""",
        }
        return examples.get(tone, examples["professional"])

    def get_parameters(self):
        return {
            "tone": {
                "type": "string",
                "enum": ["professional", "friendly", "empathetic", "authoritative", "casual", "educational"],
                "default": "professional",
                "description": "Overall tone of communication",
            },
            "formality": {
                "type": "string",
                "enum": ["formal", "balanced", "informal"],
                "default": "balanced",
                "description": "Level of formality in language",
            },
            "brand_voice": {
                "type": "string",
                "default": "",
                "description": "Optional brand voice guidelines",
            },
            "audience": {
                "type": "string",
                "enum": ["general", "technical", "executive", "customer", "internal", "academic"],
                "default": "general",
                "description": "Target audience type",
            },
        }
