"""Template factory registry."""

from schema.prompt_generator import TemplateType

from .templates.chain_of_thought import TEMPLATE as chain_of_thought
from .templates.few_shot import TEMPLATE as few_shot
from .templates.react import TEMPLATE as react
from .templates.zero_shot import TEMPLATE as zero_shot
from .templates.role_play import TEMPLATE as role_play


TEMPLATE_FACTORY = {
    TemplateType.CHAIN_OF_THOUGHT.value: chain_of_thought,
    TemplateType.FEW_SHOT.value: few_shot,
    TemplateType.REACT.value: react,
    TemplateType.ZERO_SHOT.value: zero_shot,
    TemplateType.ROLE_PLAY.value: role_play,
}


def get_template(template_type: TemplateType) -> dict:
    """Get template by type."""
    return TEMPLATE_FACTORY[template_type.value]


def get_all_templates() -> list[dict]:
    """Get all available templates."""
    return list(TEMPLATE_FACTORY.values())


def get_template_descriptions() -> str:
    """Get formatted descriptions of all templates for LLM prompt."""
    descriptions = []
    for template_type, template in TEMPLATE_FACTORY.items():
        use_cases = ", ".join(template["use_cases"])
        descriptions.append(
            f"- {template_type}: {template['description']} Use cases: {use_cases}"
        )
    return "\n".join(descriptions)
