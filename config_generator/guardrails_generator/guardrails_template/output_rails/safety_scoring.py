"""Safety Scoring output guardrail."""

GUARDRAIL = {
    "type": "safety_scoring",
    "category": "output",
    "name": "Safety Scoring",
    "description": "Score output safety across multiple dimensions and enforce thresholds.",
    "default_config": {
        "scoring_dimensions": [
            "toxicity",
            "bias",
            "harmful_advice",
            "misinformation",
            "privacy_leak",
        ],
        "thresholds": {
            "toxicity": 0.3,
            "bias": 0.4,
            "harmful_advice": 0.2,
            "misinformation": 0.3,
            "privacy_leak": 0.1,
        },
        "action": "reject",  # reject | warn | log
        "aggregate_method": "max",  # max | average | weighted
        "weights": {},  # weights for weighted aggregation
        "log_scores": True,
        "include_explanation": True,
        "enabled": True,
    },
    "use_cases": [
        "High-risk applications",
        "Compliance requirements",
        "Quality assurance",
        "Model monitoring",
        "A/B testing safety",
    ],
}
