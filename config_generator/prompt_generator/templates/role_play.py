"""Role Play prompt template."""

TEMPLATE = {
    "type": "role_play",
    "name": "Role Play",
    "description": "Establishes a specific persona with detailed characteristics. Best for conversational agents with distinct personalities.",
    "structure": """You are {role}.

## Character Profile
- Personality: {personality}
- Speaking style: {speaking_style}
- Background: {background}

## Behavior Guidelines
{behavior_guidelines}

## Context
{context}

{constraints}

Stay in character at all times and respond as {role} would.""",
    "use_cases": [
        "Customer service agents",
        "Virtual assistants with personality",
        "Educational tutors",
        "Interactive storytelling",
        "Domain-specific experts",
    ],
}
