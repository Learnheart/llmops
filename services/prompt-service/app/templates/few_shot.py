"""Few-shot prompt strategy."""

from app.templates.base import PromptStrategy


class FewShotStrategy(PromptStrategy):
    """Generates prompts with example interactions.

    This strategy creates system prompts that include example
    question-answer pairs to demonstrate expected behavior.
    Ideal for tasks where examples help clarify expectations.
    """

    name = "few_shot"
    description = "Generates prompts with example Q&A pairs to demonstrate expected behavior"

    def build_prompt(self, agent_instruction: str) -> str:
        return f"""You are an expert prompt engineer. Based on the following agent instruction,
create a FEW-SHOT system prompt for an AI assistant.

Requirements:
- Include 2-3 example interactions (Q&A pairs)
- Examples should demonstrate ideal responses
- Show the expected format and tone
- Examples should cover different scenarios
- Make examples realistic and relevant

The prompt structure should be:
1. Role and task description
2. Guidelines for responses
3. Example 1: User query → Assistant response
4. Example 2: User query → Assistant response
5. Example 3: User query → Assistant response (edge case)
6. Final instructions

Agent Instruction:
{agent_instruction}

Generate a few-shot system prompt with examples:"""
