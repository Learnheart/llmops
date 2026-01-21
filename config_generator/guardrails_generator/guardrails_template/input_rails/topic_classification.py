"""Topic Classification input guardrail."""

GUARDRAIL = {
    "type": "topic_classification",
    "category": "input",
    "name": "Topic Classification",
    "description": "Classify input topics and filter out-of-scope or prohibited topics.",
    "default_config": {
        "allowed_topics": [],  # Empty = all topics allowed
        "blocked_topics": [
            "violence",
            "illegal_activities",
            "adult_content",
            "hate_speech",
        ],
        "action": "reject",  # reject | redirect | warn
        "redirect_message": "I can only help with topics related to {allowed_topics}.",
        "confidence_threshold": 0.7,
        "custom_classifier": None,  # custom classification model/endpoint
        "enabled": True,
    },
    "use_cases": [
        "Domain-specific assistants",
        "Customer support bots",
        "Educational platforms",
        "Content-restricted applications",
    ],
}
