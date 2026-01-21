"""Chain of Thought prompt template."""

TEMPLATE = {
    "type": "chain_of_thought",
    "name": "Chain of Thought",
    "description": "Guides the model to think step-by-step before providing an answer. Best for complex reasoning tasks.",
    "structure": """You are {role}.

{context}

When answering questions, follow these steps:
1. Understand the question and identify key information
2. Break down the problem into smaller parts
3. Reason through each part systematically
4. Combine your reasoning to form a conclusion

{constraints}

Let's think step by step.""",
    "use_cases": [
        "Complex reasoning tasks",
        "Math problems",
        "Logic puzzles",
        "Multi-step analysis",
        "Decision making",
    ],
}
