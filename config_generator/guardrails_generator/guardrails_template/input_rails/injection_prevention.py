"""Injection Prevention input guardrail."""

GUARDRAIL = {
    "type": "injection_prevention",
    "category": "input",
    "name": "Injection Prevention",
    "description": "Detect and prevent prompt injection, jailbreak attempts, and malicious instructions.",
    "default_config": {
        "detect_types": [
            "prompt_injection",
            "jailbreak",
            "role_escape",
            "instruction_override",
            "delimiter_attack",
        ],
        "action": "reject",  # reject | warn | sanitize
        "sensitivity": "medium",  # low | medium | high
        "custom_patterns": [],  # additional patterns to detect
        "allowed_instructions": [],  # whitelist of allowed instruction patterns
        "log_attempts": True,
        "enabled": True,
    },
    "use_cases": [
        "Security-critical applications",
        "Public-facing chatbots",
        "Enterprise assistants",
        "Any agent handling untrusted input",
    ],
}
