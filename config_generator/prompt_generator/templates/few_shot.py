"""Few Shot prompt template."""

TEMPLATE = {
    "type": "few_shot",
    "name": "Few Shot",
    "description": "Provides examples to guide the model's response format and style. Best for tasks requiring consistent output format.",
    "structure": """You are {role}.

{context}

Here are some examples:

{examples}

{constraints}

Now, please respond in the same format as the examples above.""",
    "use_cases": [
        "Classification tasks",
        "Consistent formatting",
        "Pattern-based responses",
        "Data extraction",
        "Translation tasks",
    ],
}
