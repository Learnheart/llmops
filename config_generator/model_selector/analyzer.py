"""Analyzer module for model selection."""

import json
from llm import model_pool, LLMModel, ChatMessage
from schema.model_selector import ModelSelectorOutput


SELECTION_PROMPT = """You are an expert at selecting the best LLM model for a given task.

## Available Models:
{model_descriptions}

## Agent Description:
{agent_description}

## Instructions:
Analyze the agent description and select the most suitable model from the available options.
Consider:
1. Task complexity and type (code, reasoning, general, creative, etc.)
2. Required accuracy vs speed trade-off
3. Model tags and capabilities
4. Context length requirements

Return ONLY valid JSON with:
- selected: the model name (must be one from the available models)
- reasoning: brief explanation of why this model is the best fit

Example output:
{{
    "selected": "model-name",
    "reasoning": "This model is best because..."
}}"""


def _format_model_descriptions() -> str:
    """Format model info from pool into descriptions for prompt."""
    models = model_pool.list_llm_models()
    descriptions = []

    for name in models:
        info = model_pool.get_model_info(name)
        if info:
            tags = ", ".join(info.get("tags", []))
            desc = info.get("description", "No description")
            ctx = info.get("context_length", "N/A")
            descriptions.append(
                f"- {name}: {desc} | Tags: [{tags}] | Context: {ctx}"
            )

    return "\n".join(descriptions)


def select_model(
    llm: LLMModel,
    agent_description: str,
) -> ModelSelectorOutput:
    """
    Analyze agent description and select the most suitable LLM model.

    Args:
        llm: Loaded LLMModel instance for analysis
        agent_description: User's description of the desired agent

    Returns:
        ModelSelectorOutput with selected model and reasoning

    Raises:
        ValueError: If LLM response cannot be parsed or model not found
    """
    model_descriptions = _format_model_descriptions()
    available_models = model_pool.list_llm_models()

    # Fallback if only one model available
    if len(available_models) == 1:
        return ModelSelectorOutput(
            selected=available_models[0],
            reasoning="Only one model available in the system."
        )

    # Fallback if no models available
    if len(available_models) == 0:
        raise ValueError("No LLM models configured in the system.")

    prompt = SELECTION_PROMPT.format(
        model_descriptions=model_descriptions,
        agent_description=agent_description,
    )

    messages = [
        ChatMessage(role="user", content=prompt)
    ]

    response = llm.chat(messages, max_tokens=512, temperature=0.3)

    try:
        result = json.loads(response)
        selected = result["selected"]

        # Validate selected model exists
        if selected not in available_models:
            raise ValueError(
                f"LLM selected '{selected}' which is not available. "
                f"Available: {available_models}"
            )

        return ModelSelectorOutput(
            selected=selected,
            reasoning=result["reasoning"],
        )
    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Failed to parse LLM response: {response}") from e
