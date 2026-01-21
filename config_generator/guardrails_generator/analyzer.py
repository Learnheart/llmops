"""Analyzer module for guardrails selection and config generation."""

import json
from llm.models import LLMModel, ChatMessage
from schema.guardrails_generator import (
    GuardrailType,
    GuardrailCategory,
    AnalysisResult,
    GeneratedGuardrail,
    GuardrailsGeneratorOutput,
)
from .factory import get_guardrail, get_guardrails_descriptions


ANALYSIS_PROMPT = """You are an expert AI safety engineer. Analyze the following agent description and determine the appropriate guardrails for both input and output.

## Available Guardrails:
{guardrails_descriptions}

## Agent Description:
{agent_description}

## Instructions:
Analyze the agent description and return a JSON object with:
1. input_guardrails: list of input guardrail types that should be applied
2. output_guardrails: list of output guardrail types that should be applied
3. reasoning: why you chose these guardrails
4. risk_factors: list of identified risks (e.g., "handles PII", "public-facing", "financial data")
5. domain: the domain/industry of this agent
6. sensitivity_level: low, medium, or high based on the risk assessment

Consider:
- What type of data will the agent handle?
- Who are the users (internal/external, trusted/untrusted)?
- What are the potential risks and compliance requirements?
- What output quality and safety standards are needed?

Return ONLY valid JSON, no additional text.

Example output:
{{
    "input_guardrails": ["validation_sanitize", "pii_detection", "injection_prevention"],
    "output_guardrails": ["content_filtering", "safety_scoring"],
    "reasoning": "The agent handles customer data and is public-facing, requiring strong input validation and PII protection. Output needs content filtering for brand safety.",
    "risk_factors": ["handles PII", "public-facing", "customer data"],
    "domain": "customer support",
    "sensitivity_level": "high"
}}"""


CONFIG_GENERATION_PROMPT = """You are an expert AI safety engineer. Customize the guardrail configuration for the specific agent.

## Guardrail:
- Type: {guardrail_type}
- Name: {guardrail_name}
- Description: {guardrail_description}
- Default Config: {default_config}

## Agent Analysis:
- Domain: {domain}
- Sensitivity Level: {sensitivity_level}
- Risk Factors: {risk_factors}

## Original Agent Description:
{agent_description}

## Instructions:
Customize the default configuration for this specific agent. Consider:
- The domain and use case
- The sensitivity level
- The identified risk factors
- Specific requirements from the agent description

Return ONLY a valid JSON object with the customized configuration. Keep all keys from default config, modify values as needed.
Do not add explanations, just return the JSON config."""


def analyze_and_select_guardrails(
    llm: LLMModel,
    agent_description: str,
) -> AnalysisResult:
    """Analyze agent description and select appropriate guardrails."""
    guardrails_descriptions = get_guardrails_descriptions()

    prompt = ANALYSIS_PROMPT.format(
        guardrails_descriptions=guardrails_descriptions,
        agent_description=agent_description,
    )

    messages = [
        ChatMessage(role="user", content=prompt)
    ]

    response = llm.chat(messages, max_tokens=1024, temperature=0.3)

    try:
        result = json.loads(response)
        return AnalysisResult(
            input_guardrails=[GuardrailType(g) for g in result["input_guardrails"]],
            output_guardrails=[GuardrailType(g) for g in result["output_guardrails"]],
            reasoning=result["reasoning"],
            risk_factors=result.get("risk_factors", []),
            domain=result["domain"],
            sensitivity_level=result.get("sensitivity_level", "medium"),
        )
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        raise ValueError(f"Failed to parse LLM response: {response}") from e


def generate_guardrail_config(
    llm: LLMModel,
    guardrail_type: GuardrailType,
    analysis: AnalysisResult,
    agent_description: str,
    priority: int,
) -> GeneratedGuardrail:
    """Generate customized config for a specific guardrail."""
    guardrail = get_guardrail(guardrail_type)

    prompt = CONFIG_GENERATION_PROMPT.format(
        guardrail_type=guardrail_type.value,
        guardrail_name=guardrail["name"],
        guardrail_description=guardrail["description"],
        default_config=json.dumps(guardrail["default_config"], indent=2),
        domain=analysis.domain,
        sensitivity_level=analysis.sensitivity_level,
        risk_factors=", ".join(analysis.risk_factors),
        agent_description=agent_description,
    )

    messages = [
        ChatMessage(role="user", content=prompt)
    ]

    response = llm.chat(messages, max_tokens=1024, temperature=0.3)

    try:
        config = json.loads(response)
    except json.JSONDecodeError:
        # Fallback to default config if LLM response is invalid
        config = guardrail["default_config"].copy()

    return GeneratedGuardrail(
        type=guardrail_type,
        category=GuardrailCategory(guardrail["category"]),
        name=guardrail["name"],
        config=config,
        priority=priority,
    )


def analyze_and_generate(
    llm: LLMModel,
    agent_description: str,
) -> GuardrailsGeneratorOutput:
    """Main entry point: analyze description and generate guardrail configs.

    Args:
        llm: Loaded LLMModel instance
        agent_description: User's description of the desired agent

    Returns:
        GuardrailsGeneratorOutput containing analysis and generated guardrails
    """
    # Step 1: Analyze and select guardrails
    analysis = analyze_and_select_guardrails(llm, agent_description)

    # Step 2: Generate configs for input guardrails
    input_guardrails = []
    for priority, guardrail_type in enumerate(analysis.input_guardrails, start=1):
        guardrail = generate_guardrail_config(
            llm=llm,
            guardrail_type=guardrail_type,
            analysis=analysis,
            agent_description=agent_description,
            priority=priority,
        )
        input_guardrails.append(guardrail)

    # Step 3: Generate configs for output guardrails
    output_guardrails = []
    for priority, guardrail_type in enumerate(analysis.output_guardrails, start=1):
        guardrail = generate_guardrail_config(
            llm=llm,
            guardrail_type=guardrail_type,
            analysis=analysis,
            agent_description=agent_description,
            priority=priority,
        )
        output_guardrails.append(guardrail)

    return GuardrailsGeneratorOutput(
        analysis=analysis,
        input_guardrails=input_guardrails,
        output_guardrails=output_guardrails,
    )
