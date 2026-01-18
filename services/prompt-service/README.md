# Prompt Service

LLMOps Platform - Prompt Generation and Management Service

## Features

- **Template-based Prompt Generation**: Generate prompts using predefined strategies (concise, detailed, step-by-step, few-shot)
- **Prompt Versioning**: Track changes to prompts with full version history
- **Variant Management**: Create and manage multiple variants of generated prompts
- **Audit Logging**: Complete history of all changes for compliance and debugging

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     PROMPT SERVICE                          │
├─────────────────────────────────────────────────────────────┤
│  Templates (CODE)           │  Data (DATABASE)              │
│  ─────────────────         │  ──────────────────           │
│  • concise                  │  • prompt_generations         │
│  • detailed                 │  • prompt_variants            │
│  • step_by_step             │  • prompt_variant_history     │
│  • few_shot                 │                               │
│                             │                               │
│  Managed by: Developers     │  Managed by: Users            │
│  Storage: Python Code       │  Storage: PostgreSQL          │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Using Docker Compose (from project root)

This service is **stateless** and depends on shared infrastructure (PostgreSQL, NATS, etc.).
Run from the project root directory:

```bash
# From project root (LLMOps_v2/)
cp .env.example .env

# Edit .env with your settings
# ...

# Start all infrastructure + prompt-service
docker-compose up -d

# Or start only prompt-service (after infrastructure is running)
docker-compose up -d prompt-service

# Check health
curl http://localhost:8080/health
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start server (tables auto-created on startup)
uvicorn app.main:app --reload --port 8080
```

## API Endpoints

### Health
- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed health with DB status
- `GET /ready` - Kubernetes readiness probe
- `GET /live` - Kubernetes liveness probe

### Templates (Read-only)
- `GET /api/v1/templates` - List all templates
- `GET /api/v1/templates/keys` - Get template keys
- `GET /api/v1/templates/{key}` - Get template details
- `POST /api/v1/templates/{key}/preview` - Preview a prompt

### Prompts
- `POST /api/v1/prompts/compose` - Compose a prompt
- `POST /api/v1/prompts/batch-compose` - Batch compose
- `POST /api/v1/prompts/compare` - Compare templates

### Generations
- `POST /api/v1/generations` - Generate and save prompt
- `GET /api/v1/generations` - List user's generations
- `GET /api/v1/generations/{id}` - Get generation
- `DELETE /api/v1/generations/{id}` - Delete generation
- `GET /api/v1/generations/{id}/variants` - List variants

### Variants
- `POST /api/v1/variants` - Create variant
- `GET /api/v1/variants` - List user's variants
- `GET /api/v1/variants/{id}` - Get variant
- `PUT /api/v1/variants/{id}` - Update variant (new version)
- `POST /api/v1/variants/{id}/activate` - Activate/deactivate
- `POST /api/v1/variants/{id}/status` - Change status
- `GET /api/v1/variants/{id}/history` - Get audit history

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| SERVICE_NAME | prompt-service | Service name |
| SERVICE_PORT | 8080 | Service port |
| LOG_LEVEL | INFO | Logging level |
| POSTGRES_HOST | postgres | PostgreSQL host |
| POSTGRES_PORT | 5432 | PostgreSQL port |
| POSTGRES_USER | llmops | Database user |
| POSTGRES_PASSWORD | - | Database password |
| POSTGRES_DB | llmops | Database name |
| NATS_URL | nats://nats:4222 | NATS server URL |
| OPENAI_API_KEY | - | OpenAI API key |
| ANTHROPIC_API_KEY | - | Anthropic API key |
| GROQ_API_KEY | - | Groq API key |
| DEFAULT_LLM_PROVIDER | groq | Default LLM provider |

## Project Structure

```
prompt-service/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── api/
│   │   └── routes/          # API endpoints
│   │       ├── health.py
│   │       ├── templates.py
│   │       ├── generations.py
│   │       ├── variants.py
│   │       └── prompts.py
│   ├── models/
│   │   ├── database.py      # SQLAlchemy models
│   │   └── schemas.py       # Pydantic schemas
│   ├── repositories/        # Data access layer
│   │   ├── generation_repository.py
│   │   ├── variant_repository.py
│   │   └── history_repository.py
│   ├── services/            # Business logic
│   │   ├── template_service.py
│   │   ├── prompt_service.py
│   │   ├── variant_service.py
│   │   └── llm_service.py
│   └── templates/           # Prompt strategies (CODE)
│       ├── base.py
│       ├── registry.py
│       ├── concise.py
│       ├── detailed.py
│       ├── step_by_step.py
│       └── few_shot.py
├── Dockerfile
├── requirements.txt
└── README.md
```

## License

Proprietary - LLMOps Platform
