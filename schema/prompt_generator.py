"""Pydantic models for Prompt Generator module."""

from enum import Enum
from pydantic import BaseModel


class TemplateType(str, Enum):
    """Supported prompt template types."""
    CHAIN_OF_THOUGHT = "chain_of_thought"
    FEW_SHOT = "few_shot"
    REACT = "react"
    ZERO_SHOT = "zero_shot"
    ROLE_PLAY = "role_play"


class TemplateInfo(BaseModel):
    """Template metadata and structure."""
    type: TemplateType
    name: str
    description: str
    structure: str
    use_cases: list[str]


class AnalysisResult(BaseModel):
    """Result from LLM analysis of agent description."""
    selected_templates: list[TemplateType]
    reasoning: str
    domain: str
    tone: str
    constraints: list[str]
    key_capabilities: list[str]


class GeneratedPrompt(BaseModel):
    """A generated prompt from template."""
    template_type: TemplateType
    prompt: str
    metadata: dict


class PromptGeneratorInput(BaseModel):
    """Input for prompt generator."""
    agent_description: str


class PromptGeneratorOutput(BaseModel):
    """Output from prompt generator."""
    analysis: AnalysisResult
    generated_prompts: list[GeneratedPrompt]
