"""Concise prompt strategy."""

from app.templates.base import PromptStrategy


class ConciseStrategy(PromptStrategy):
    """Generates short, focused prompts.

    This strategy creates brief, clear system prompts that are
    direct and to the point. Ideal for simple, straightforward tasks.
    """

    name = "concise"
    description = "Generates short, focused prompts that are brief and to the point"

    def build_prompt(self, agent_instruction: str) -> str:
        return f"""You are an expert prompt engineer. Based on the following agent instruction,
create a CONCISE system prompt for an AI assistant.

Requirements:
- Keep it brief, clear, and to the point
- Maximum 150 words
- Focus on the core task only
- Use simple, direct language
- Avoid unnecessary elaboration

Agent Instruction:
{agent_instruction}

Generate a concise system prompt:"""
