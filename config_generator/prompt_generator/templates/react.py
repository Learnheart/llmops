"""ReAct (Reasoning + Acting) prompt template."""

TEMPLATE = {
    "type": "react",
    "name": "ReAct",
    "description": "Combines reasoning and acting in an interleaved manner. Best for tasks requiring tool use or external interactions.",
    "structure": """You are {role}.

{context}

You have access to the following tools:
{tools}

Use this format:

Question: the input question you must answer
Thought: think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (repeat Thought/Action/Action Input/Observation as needed)
Thought: I now know the final answer
Final Answer: the final answer to the question

{constraints}

Begin!""",
    "use_cases": [
        "Tool-using agents",
        "Information retrieval",
        "API interactions",
        "Multi-step tasks with external data",
        "Research assistants",
    ],
}
