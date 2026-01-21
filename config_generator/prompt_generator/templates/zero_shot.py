"""Zero Shot prompt template."""

TEMPLATE = {
    "type": "zero_shot",
    "name": "Zero Shot",
    "description": "Direct instruction without examples. Best for straightforward tasks where the model can infer the expected behavior.",
    "structure": """You are {role}.

{context}

Your task: {task}

{constraints}

Please provide your response.""",
    "use_cases": [
        "Simple Q&A",
        "Straightforward tasks",
        "General knowledge queries",
        "Summarization",
        "Basic text generation",
    ],
}
