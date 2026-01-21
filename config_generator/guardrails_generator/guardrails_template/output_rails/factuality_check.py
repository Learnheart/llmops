"""Factuality Check output guardrail."""

GUARDRAIL = {
    "type": "factuality_check",
    "category": "output",
    "name": "Factuality Check",
    "description": "Verify factual accuracy of model output and detect hallucinations.",
    "default_config": {
        "check_types": [
            "numerical_claims",
            "date_claims",
            "named_entities",
            "citations",
            "statistics",
        ],
        "action": "flag",  # flag | reject | append_disclaimer
        "confidence_threshold": 0.8,
        "require_sources": False,
        "knowledge_base": None,  # reference knowledge base for verification
        "disclaimer_text": "Note: This information should be independently verified.",
        "max_uncertainty_score": 0.3,
        "enabled": True,
    },
    "use_cases": [
        "News and journalism",
        "Medical information",
        "Legal advice",
        "Educational content",
        "Research assistance",
    ],
}
