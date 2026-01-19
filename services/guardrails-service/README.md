# Guardrails Service

LLMOps Platform - Guardrails Service for creating and managing AI safety guardrails.

## Overview

The Guardrails Service provides a comprehensive framework for creating, managing, and versioning guardrails that ensure safe, compliant, and high-quality AI interactions. This service is **stateless** - it does not store user data, only guardrail definitions and configurations.

## Features

### 🛡️ Pre-built Templates
- **Content Safety**: Prevent harmful or inappropriate content
- **PII Protection**: Protect personally identifiable information
- **Factual Accuracy**: Ensure accuracy and prevent hallucinations
- **Tone Control**: Maintain appropriate communication style
- **Compliance**: Ensure regulatory compliance (GDPR, HIPAA, CCPA, etc.)

### 🔧 Template Customization
- Generate guardrails from templates with custom parameters
- Preview guardrails before saving
- Compare multiple templates side-by-side

### 📝 Variant Management
- Save customized guardrails as variants
- Version control with automatic versioning
- Activate/deactivate variants
- Status management (draft, active, archived)

### 📊 History & Audit
- Complete audit trail for all changes
- Track variant creation, updates, and status changes
- Rollback capabilities through history

### 🚀 Batch Operations
- Generate multiple guardrails at once
- Bulk comparison of templates

## Architecture

### Directory Structure

```
guardrails-service/
├── Dockerfile                          # Container configuration
├── requirements.txt                    # Python dependencies
├── README.md                          # This file
├── .env.example                       # Environment variables template
└── app/
    ├── __init__.py
    ├── main.py                        # FastAPI application
    ├── config.py                      # Configuration management
    ├── api/
    │   ├── __init__.py
    │   └── routes/
    │       ├── __init__.py
    │       ├── health.py             # Health check endpoints
    │       ├── templates.py          # Template browsing
    │       ├── generations.py        # Guardrail generation
    │       ├── variants.py           # Variant management
    │       └── guardrails.py         # High-level operations
    ├── models/
    │   ├── __init__.py
    │   ├── database.py              # SQLAlchemy models
    │   └── schemas.py               # Pydantic schemas
    ├── repositories/                # Data access layer
    │   ├── __init__.py
    │   ├── generation_repository.py
    │   ├── variant_repository.py
    │   └── history_repository.py
    ├── services/                    # Business logic
    │   ├── __init__.py
    │   ├── llm_service.py          # LLM integration
    │   ├── template_service.py     # Template operations
    │   ├── guardrail_service.py    # Guardrail generation
    │   └── variant_service.py      # Variant management
    └── templates/                   # Guardrail strategies
        ├── __init__.py
        ├── base.py                 # Base strategy class
        ├── registry.py             # Template registry
        ├── content_safety.py       # Content safety template
        ├── pii_protection.py       # PII protection template
        ├── factual_accuracy.py     # Factual accuracy template
        ├── tone_control.py         # Tone control template
        └── compliance.py           # Compliance template
```

### Design Patterns

1. **Factory Pattern**: Template registry for creating guardrail strategies
2. **Strategy Pattern**: Different guardrail generation algorithms
3. **Repository Pattern**: Database access abstraction
4. **Service Layer**: Business logic orchestration
5. **Dependency Injection**: Database session management

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Groq API Key (or OpenAI/Anthropic)

### Installation

1. Clone the repository:
```bash
cd services/guardrails-service
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run the service:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8083 --reload
```

### Using Docker

1. Build the image:
```bash
docker build -t guardrails-service .
```

2. Run the container:
```bash
docker run -p 8083:8083 \
  -e POSTGRES_HOST=host.docker.internal \
  -e POSTGRES_PASSWORD=your_password \
  -e GROQ_API_KEY=your_api_key \
  guardrails-service
```

## API Usage

The service supports **2 modes** for generating guardrails:
- **Manual Mode**: You choose the template
- **Auto Mode**: AI automatically selects the best template

See [USAGE_MODES.md](USAGE_MODES.md) for detailed guide.

### Browse Available Templates

```bash
curl http://localhost:8083/api/v1/templates
```

### Preview a Template

```bash
curl -X POST http://localhost:8083/api/v1/templates/content_safety/preview \
  -H "Content-Type: application/json" \
  -d '{
    "user_context": "Customer support chatbot for a healthcare company",
    "parameters": {
      "safety_level": "strict",
      "custom_topics": ["medical diagnoses", "treatment recommendations"]
    }
  }'
```

### Generate a Guardrail (Manual Mode)

```bash
curl -X POST http://localhost:8083/api/v1/generations \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "mode": "manual",
    "template_key": "content_safety",
    "user_context": "Customer support chatbot",
    "parameters": {
      "safety_level": "standard"
    }
  }'
```

### Generate a Guardrail (Auto Mode - AI selects template)

```bash
curl -X POST http://localhost:8083/api/v1/generations \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "mode": "auto",
    "user_context": "Healthcare chatbot handling patient medical records",
    "instruction": "Need HIPAA compliance and protect patient privacy",
    "parameters": {}
  }'
```
→ AI will analyze and select the best template (e.g., `compliance` or `pii_protection`)

### Create a Variant

```bash
curl -X POST http://localhost:8083/api/v1/variants \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "generation_id": "generation-uuid-here",
    "name": "Production Content Safety Rules",
    "description": "Customized safety rules for production environment",
    "status": "active"
  }'
```

### Compare Templates

```bash
curl -X POST http://localhost:8083/api/v1/guardrails/compare \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "template_keys": ["content_safety", "pii_protection", "compliance"],
    "user_context": "Healthcare chatbot handling patient inquiries"
  }'
```

## Configuration

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVICE_PORT` | HTTP port | 8083 |
| `POSTGRES_HOST` | Database host | postgres |
| `POSTGRES_PORT` | Database port | 5432 |
| `POSTGRES_DB` | Database name | llmops |
| `GROQ_API_KEY` | Groq API key | - |
| `DEFAULT_LLM_PROVIDER` | LLM provider | groq |

See `.env.example` for full configuration options.

## Database Schema

### Tables

1. **guardrail_generations**: Stores generated guardrails
2. **guardrail_variants**: User-customized variants with versioning
3. **guardrail_variant_history**: Audit log for all changes

### Relationships

- One generation can have multiple variants
- One variant can have multiple history entries
- Cascade delete: Deleting a generation deletes its variants

## Available Templates

### 1. Content Safety
Prevents harmful, offensive, or inappropriate content.

**Parameters**:
- `safety_level`: strict, standard, lenient
- `custom_topics`: array of topics to restrict

### 2. PII Protection
Protects personally identifiable information.

**Parameters**:
- `pii_types`: types of PII to protect
- `redaction_strategy`: mask, remove, generalize

### 3. Factual Accuracy
Ensures accuracy and prevents hallucinations.

**Parameters**:
- `citation_required`: boolean
- `uncertainty_threshold`: strict, medium, lenient
- `domain`: general, medical, legal, financial, scientific, technical

### 4. Tone Control
Maintains appropriate tone and communication style.

**Parameters**:
- `tone`: professional, friendly, empathetic, authoritative, casual, educational
- `formality`: formal, balanced, informal
- `brand_voice`: custom brand guidelines
- `audience`: general, technical, executive, customer, internal, academic

### 5. Compliance
Ensures regulatory compliance.

**Parameters**:
- `regulations`: array of regulations (GDPR, HIPAA, CCPA, etc.)
- `jurisdiction`: legal jurisdiction
- `industry`: general, healthcare, finance, education, retail

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Style

```bash
# Format code
black app/

# Lint code
flake8 app/

# Type checking
mypy app/
```

### Adding New Templates

1. Create template file in `app/templates/`
2. Inherit from `GuardrailStrategy`
3. Implement `build_guardrail()` method
4. Register in `app/templates/registry.py`

Example:

```python
from app.templates.base import GuardrailStrategy

class MyGuardrailStrategy(GuardrailStrategy):
    name = "my_guardrail"
    description = "My custom guardrail"
    category = "quality"

    def build_guardrail(self, user_context: str, **kwargs) -> str:
        # Your implementation here
        return f"Guardrail content for {user_context}"
```

## Health Checks

- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed health with database status
- `GET /ready` - Kubernetes readiness probe
- `GET /live` - Kubernetes liveness probe

## API Documentation

- Swagger UI: http://localhost:8083/docs
- ReDoc: http://localhost:8083/redoc
- OpenAPI JSON: http://localhost:8083/openapi.json

## License

MIT License

## Support

For issues or questions, please open an issue on GitHub.
