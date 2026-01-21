"""PII Detection & Masking input guardrail."""

GUARDRAIL = {
    "type": "pii_detection",
    "category": "input",
    "name": "PII Detection & Masking",
    "description": "Detect and mask personally identifiable information in user input.",
    "default_config": {
        "detect_types": [
            "email",
            "phone",
            "ssn",
            "credit_card",
            "address",
            "name",
            "date_of_birth",
            "ip_address",
        ],
        "action": "mask",  # mask | reject | warn
        "mask_char": "*",
        "mask_preserve_length": True,
        "custom_patterns": {},  # regex patterns for custom PII
        "whitelist": [],  # patterns to ignore
        "enabled": True,
    },
    "use_cases": [
        "Privacy protection",
        "GDPR compliance",
        "Healthcare data protection",
        "Financial data security",
    ],
}
