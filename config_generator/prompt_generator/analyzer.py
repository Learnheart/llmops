"""Analyzer module for template selection and prompt generation."""

import json
from llm.models import LLMModel, ChatMessage
from schema.prompt_generator import (
    TemplateType,
    AnalysisResult,
    GeneratedPrompt,
    PromptGeneratorOutput,
)
from .factory import get_template, get_template_descriptions


ANALYSIS_PROMPT = """You are an expert prompt engineer. Analyze the following agent description and determine the best prompt template(s) to use.

## Available Templates:
{template_descriptions}

## Agent Description:
{agent_description}

## Instructions:
Analyze the agent description and return a JSON object with:
1. selected_templates: list of template types that best fit this agent (choose 1-3 templates)
2. reasoning: why you chose these templates
3. domain: the domain/industry of this agent
4. tone: the desired tone (professional, friendly, formal, casual, etc.)
5. constraints: list of any constraints or limitations mentioned
6. key_capabilities: list of main capabilities the agent should have

Return ONLY valid JSON, no additional text.

Example output:
{{
    "selected_templates": ["chain_of_thought", "few_shot"],
    "reasoning": "The agent needs to solve complex problems step by step and requires consistent output format",
    "domain": "customer support",
    "tone": "professional",
    "constraints": ["must not share personal data", "response under 200 words"],
    "key_capabilities": ["answer questions", "provide solutions", "escalate issues"]
}}"""


GENERATION_PROMPT = """You are an expert prompt engineer. Generate a complete prompt for an AI agent based on the template and analysis below.

## Template Structure:
{template_structure}

## Analysis:
- Domain: {domain}
- Tone: {tone}
- Key Capabilities: {key_capabilities}
- Constraints: {constraints}

## Original Agent Description:
{agent_description}

## Instructions:
Fill in the template structure with appropriate content based on the analysis and agent description.
Create a complete, ready-to-use prompt that:
1. Fills all placeholder variables ({{role}}, {{context}}, etc.)
2. Matches the desired tone
3. Incorporates the key capabilities
4. Includes all constraints

Return ONLY the final prompt text, no additional explanation."""


def analyze_and_select_templates(
    llm: LLMModel,
    agent_description: str,
) -> AnalysisResult:
    """Analyze agent description and select appropriate templates."""
    template_descriptions = get_template_descriptions()

    prompt = ANALYSIS_PROMPT.format(
        template_descriptions=template_descriptions,
        agent_description=agent_description,
    )

    messages = [
        ChatMessage(role="user", content=prompt)
    ]

    response = llm.chat(messages, max_tokens=1024, temperature=0.3)

    try:
        result = json.loads(response)
        return AnalysisResult(
            selected_templates=[TemplateType(t) for t in result["selected_templates"]],
            reasoning=result["reasoning"],
            domain=result["domain"],
            tone=result["tone"],
            constraints=result.get("constraints", []),
            key_capabilities=result.get("key_capabilities", []),
        )
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        raise ValueError(f"Failed to parse LLM response: {response}") from e


def generate_prompt_from_template(
    llm: LLMModel,
    template_type: TemplateType,
    analysis: AnalysisResult,
    agent_description: str,
) -> GeneratedPrompt:
    """Generate a specific prompt from template and analysis."""
    template = get_template(template_type)

    prompt = GENERATION_PROMPT.format(
        template_structure=template["structure"],
        domain=analysis.domain,
        tone=analysis.tone,
        key_capabilities=", ".join(analysis.key_capabilities),
        constraints=", ".join(analysis.constraints) if analysis.constraints else "None",
        agent_description=agent_description,
    )

    messages = [
        ChatMessage(role="user", content=prompt)
    ]

    response = llm.chat(messages, max_tokens=2048, temperature=0.7)

    return GeneratedPrompt(
        template_type=template_type,
        prompt=response.strip(),
        metadata={
            "template_name": template["name"],
            "domain": analysis.domain,
            "tone": analysis.tone,
        },
    )


def analyze_and_generate(
    llm: LLMModel,
    agent_description: str,
) -> PromptGeneratorOutput:
    """Main entry point: analyze description and generate prompts.

    Args:
        llm: Loaded LLMModel instance
        agent_description: User's description of the desired agent

    Returns:
        PromptGeneratorOutput containing analysis and generated prompts
    """
    # Step 1: Analyze and select templates
    analysis = analyze_and_select_templates(llm, agent_description)

    # Step 2: Generate prompts for each selected template
    generated_prompts = []
    for template_type in analysis.selected_templates:
        prompt = generate_prompt_from_template(
            llm=llm,
            template_type=template_type,
            analysis=analysis,
            agent_description=agent_description,
        )
        generated_prompts.append(prompt)

    return PromptGeneratorOutput(
        analysis=analysis,
        generated_prompts=generated_prompts,
    )
