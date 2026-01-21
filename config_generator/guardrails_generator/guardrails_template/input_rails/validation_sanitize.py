"""Validation & Sanitize input guardrail."""

GUARDRAIL = {
    "type": "validation_sanitize",
    "category": "input",
    "name": "Validation & Sanitize",
    "description": "Validate input format and sanitize potentially harmful characters or patterns.",
    "default_config": {
        "max_length": 4096,
        "min_length": 1,
        "strip_whitespace": True,
        "remove_html_tags": True,
        "normalize_unicode": True,
        "blocked_patterns": [],
        "allowed_languages": [],  # Empty = all languages
        "enabled": True,
    },
    "use_cases": [
        "Prevent malformed input",
        "Normalize user input",
        "Remove potentially harmful content",
        "Enforce input constraints",
    ],
}
