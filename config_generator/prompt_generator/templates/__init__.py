"""Prompt templates."""

from .chain_of_thought import TEMPLATE as CHAIN_OF_THOUGHT_TEMPLATE
from .few_shot import TEMPLATE as FEW_SHOT_TEMPLATE
from .react import TEMPLATE as REACT_TEMPLATE
from .zero_shot import TEMPLATE as ZERO_SHOT_TEMPLATE
from .role_play import TEMPLATE as ROLE_PLAY_TEMPLATE

__all__ = [
    "CHAIN_OF_THOUGHT_TEMPLATE",
    "FEW_SHOT_TEMPLATE",
    "REACT_TEMPLATE",
    "ZERO_SHOT_TEMPLATE",
    "ROLE_PLAY_TEMPLATE",
]
