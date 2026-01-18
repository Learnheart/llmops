"""Base class for prompt strategies."""

from abc import ABC, abstractmethod


class PromptStrategy(ABC):
    """Abstract base class for prompt generation strategies.

    Each strategy defines a different approach to generating prompts
    from an agent instruction. Strategies are defined in code and
    registered in the TEMPLATE_REGISTRY.

    Attributes:
        name: Unique identifier for the strategy
        description: Human-readable description of what this strategy does
    """

    name: str
    description: str

    @abstractmethod
    def build_prompt(self, agent_instruction: str) -> str:
        """Build the prompt template for LLM to generate a variant.

        Args:
            agent_instruction: The user's agent instruction/description

        Returns:
            A prompt string to send to the LLM for generating the variant
        """
        pass

    def to_dict(self) -> dict:
        """Convert strategy to dictionary representation."""
        return {
            "key": self.name,
            "name": self.name.replace("_", " ").title(),
            "description": self.description,
        }
