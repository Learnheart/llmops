"""Format Validation output guardrail."""

GUARDRAIL = {
    "type": "format_validation",
    "category": "output",
    "name": "Format Validation",
    "description": "Validate output format, structure, and schema compliance.",
    "default_config": {
        "expected_format": "text",  # text | json | markdown | html | custom
        "json_schema": None,  # JSON schema for validation
        "max_length": 4096,
        "min_length": 1,
        "required_fields": [],  # for structured output
        "forbidden_patterns": [],
        "enforce_language": None,  # enforce specific language
        "action": "retry",  # retry | truncate | reject
        "max_retries": 2,
        "enabled": True,
    },
    "use_cases": [
        "API responses",
        "Structured data extraction",
        "Form filling",
        "Code generation",
        "Template-based output",
    ],
}
