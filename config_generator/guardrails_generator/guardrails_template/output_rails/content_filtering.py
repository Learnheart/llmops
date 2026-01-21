"""Content Filtering output guardrail."""

GUARDRAIL = {
    "type": "content_filtering",
    "category": "output",
    "name": "Content Filtering",
    "description": "Filter inappropriate, harmful, or unwanted content from model output.",
    "default_config": {
        "filter_categories": [
            "profanity",
            "hate_speech",
            "violence",
            "sexual_content",
            "self_harm",
            "illegal_advice",
        ],
        "action": "redact",  # redact | reject | warn
        "replacement_text": "[Content removed]",
        "sensitivity": "medium",  # low | medium | high
        "custom_filters": [],  # additional content patterns to filter
        "allow_medical_terms": False,
        "allow_educational_content": True,
        "enabled": True,
    },
    "use_cases": [
        "Child-safe applications",
        "Corporate environments",
        "Public-facing services",
        "Regulated industries",
    ],
}
