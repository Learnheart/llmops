"""Detailed prompt strategy."""

from app.templates.base import PromptStrategy


class DetailedStrategy(PromptStrategy):
    """Generates comprehensive prompts with context.

    This strategy creates detailed system prompts that include
    context, guidelines, and clear structure. Ideal for complex tasks
    requiring specific behavior.
    """

    name = "detailed"
    description = "Generates comprehensive prompts with full context and guidelines"

    def build_prompt(self, agent_instruction: str) -> str:
        return f"""You are an expert prompt engineer. Based on the following agent instruction,
create a DETAILED system prompt for an AI assistant.

Requirements:
- Include comprehensive context and background
- Define the role clearly
- List specific capabilities and limitations
- Provide clear guidelines for behavior
- Include constraints and boundaries
- Structure the prompt with clear sections

The prompt should include:
1. Role Definition - Who is this assistant?
2. Capabilities - What can it do?
3. Constraints - What are the limitations?
4. Tone & Style - How should it communicate?
5. Guidelines - Specific rules to follow

Agent Instruction:
{agent_instruction}

Generate a detailed system prompt:"""
