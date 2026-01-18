"""Step-by-step prompt strategy."""

from app.templates.base import PromptStrategy


class StepByStepStrategy(PromptStrategy):
    """Generates prompts with chain-of-thought reasoning.

    This strategy creates system prompts that encourage the AI
    to think through problems step by step. Ideal for tasks
    requiring logical reasoning or complex problem-solving.
    """

    name = "step_by_step"
    description = "Generates prompts that encourage step-by-step reasoning"

    def build_prompt(self, agent_instruction: str) -> str:
        return f"""You are an expert prompt engineer. Based on the following agent instruction,
create a STEP-BY-STEP system prompt for an AI assistant.

Requirements:
- Design the prompt to encourage methodical thinking
- Include instructions for breaking down problems
- Emphasize showing reasoning process
- Guide the assistant to think before answering
- Include phrases like "Let's think step by step"

The prompt should encourage:
1. Understanding the problem first
2. Breaking it into smaller parts
3. Solving each part systematically
4. Verifying the solution
5. Presenting clear reasoning

Agent Instruction:
{agent_instruction}

Generate a step-by-step reasoning system prompt:"""
