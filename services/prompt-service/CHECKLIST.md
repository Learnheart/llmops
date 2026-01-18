# Prompt Service - Implementation Checklist

## Overview

Service xử lý logic liên quan đến prompt: auto-generate prompt variants hoặc parse/validate custom prompts từ user.

> **Important**:
> - Service này là **stateless** - chỉ chứa business logic, KHÔNG lưu trữ data
> - Tất cả data được lưu ở shared infrastructure bên ngoài
> - Service nhận request đã được filter từ **Orchestrator** (không nhận raw user config)

---

## Architecture Context

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATOR                                 │
│                                                                      │
│  1. Nhận full user config (JSON/YAML)                               │
│  2. Lưu full config vào DB (với request_id)                         │
│  3. Extract & gửi prompt-related fields đến Prompt Service          │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       PROMPT SERVICE                                 │
│                                                                      │
│  Input từ Orchestrator:                                             │
│  {                                                                   │
│    "request_id": "uuid",                                            │
│    "user_id": "user_123",                                           │
│    "agent_instruction": "You are a customer support agent...",      │
│    "mode": "auto_generate" | "custom_import",                       │
│    "num_variants": 4,                                               │
│    "custom_config_path": "s3://bucket/path.yaml",  // if custom     │
│    "model_params": { "temperature": 0.7, ... }     // optional      │
│  }                                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 1. Project Setup

- [ ] Khởi tạo project Python với FastAPI
- [ ] Cấu trúc thư mục theo chuẩn
- [ ] `requirements.txt` với dependencies
- [ ] `Dockerfile` cho containerization
- [ ] `.env.example` với tất cả env vars
- [ ] Config management (pydantic-settings)

---

## 2. Shared Infrastructure (External)

Service kết nối tới infrastructure đã có sẵn (từ `docker-compose.yml` gốc):

| Infrastructure | Mục đích | Internal Host |
|----------------|----------|---------------|
| **PostgreSQL** | Lưu prompts, variants, versions, metadata | `postgres:5432` |
| **NATS** | Nhận jobs từ orchestrator, publish results | `nats:4222` |
| **Elasticsearch** | Index prompts để search (Phase 5) | `elasticsearch:9200` |

> **Note**: MinIO không được sử dụng trong prompt-service. Tất cả prompt data được lưu trong PostgreSQL.

---

## 3. Data Storage Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA STORAGE SEPARATION                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────┐    ┌─────────────────────────────────────┐ │
│  │   PROMPT TEMPLATES          │    │   PROMPT GENERATED                  │ │
│  │   (System Resources)        │    │   (User Data)                       │ │
│  ├─────────────────────────────┤    ├─────────────────────────────────────┤ │
│  │                             │    │                                     │ │
│  │  Storage: CODE (Python)     │    │  Storage: PostgreSQL                │ │
│  │                             │    │                                     │ │
│  │  • Defined in source code   │    │  • prompt_generations table         │ │
│  │  • Factory Strategy Pattern │    │  • prompt_variants table            │ │
│  │  • Version controlled (Git) │    │  • prompt_variant_history table     │ │
│  │  • Deploy = code release    │    │  • Versioning per variant           │ │
│  │                             │    │                                     │ │
│  │  Access:                    │    │  Access:                            │ │
│  │  • Developer: Full control  │    │  • User: CRUD own data              │ │
│  │  • User: READ only          │    │  • System: Full access              │ │
│  │                             │    │                                     │ │
│  └─────────────────────────────┘    └─────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Prompt Templates (Code-based - NOT in Database)

> **Important**:
> - Templates được định nghĩa trong **source code**, KHÔNG lưu trong database
> - Chỉ developer mới được thay đổi (qua code commit)
> - User chỉ có thể **view** và **select** template

### 4.1 Template Strategies (Factory Pattern)

```python
# app/templates/base.py
from abc import ABC, abstractmethod

class PromptStrategy(ABC):
    name: str
    description: str

    @abstractmethod
    def build_prompt(self, agent_instruction: str) -> str:
        """Build the prompt template for LLM to generate variant"""
        pass
```

```python
# app/templates/concise.py
class ConciseStrategy(PromptStrategy):
    name = "concise"
    description = "Generates short, focused prompts"

    def build_prompt(self, agent_instruction: str) -> str:
        return f"""
        Based on the following agent instruction, create a CONCISE prompt.
        Keep it brief, clear, and to the point. Maximum 100 words.

        Agent Instruction: {agent_instruction}

        Generate a concise system prompt:
        """
```

```python
# app/templates/detailed.py
class DetailedStrategy(PromptStrategy):
    name = "detailed"
    description = "Generates comprehensive prompts with context"

    def build_prompt(self, agent_instruction: str) -> str:
        return f"""
        Based on the following agent instruction, create a DETAILED prompt.
        Include context, examples, and clear guidelines.

        Agent Instruction: {agent_instruction}

        Generate a detailed system prompt with:
        1. Role definition
        2. Capabilities
        3. Constraints
        4. Example interactions
        """
```

### 4.2 Template Registry

```python
# app/templates/registry.py
from .concise import ConciseStrategy
from .detailed import DetailedStrategy
from .step_by_step import StepByStepStrategy
from .few_shot import FewShotStrategy

TEMPLATE_REGISTRY: dict[str, PromptStrategy] = {
    "concise": ConciseStrategy(),
    "detailed": DetailedStrategy(),
    "step_by_step": StepByStepStrategy(),
    "few_shot": FewShotStrategy(),
}

def get_template(key: str) -> PromptStrategy:
    if key not in TEMPLATE_REGISTRY:
        raise TemplateNotFoundError(f"Template '{key}' not found")
    return TEMPLATE_REGISTRY[key]

def list_templates() -> list[dict]:
    return [
        {"key": k, "name": v.name, "description": v.description}
        for k, v in TEMPLATE_REGISTRY.items()
    ]
```

---

## 5. Prompt Generated (PostgreSQL Database)

Lưu **kết quả generate** và **version history** trong PostgreSQL.

### 5.1 Tables

- [ ] Table `prompt_generations`
  ```sql
  CREATE TABLE prompt_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL,           -- link to orchestrator request
    user_id VARCHAR(255) NOT NULL,
    agent_instruction TEXT NOT NULL,    -- input từ user
    created_at TIMESTAMP DEFAULT NOW()
  );
  CREATE INDEX idx_generations_user_id ON prompt_generations(user_id);
  CREATE INDEX idx_generations_request_id ON prompt_generations(request_id);
  ```

- [ ] Table `prompt_variants` (với versioning)
  ```sql
  CREATE TABLE prompt_variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    generation_id UUID NOT NULL REFERENCES prompt_generations(id) ON DELETE CASCADE,
    template_key VARCHAR(100) NOT NULL,  -- e.g., "concise", "detailed"
    version INT NOT NULL DEFAULT 1,      -- version number
    content TEXT NOT NULL,               -- generated prompt content
    is_active BOOLEAN DEFAULT TRUE,      -- current active version
    metadata JSONB,                       -- LLM info, cost, tokens, etc.
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(255),             -- user_id who created this version

    UNIQUE(generation_id, template_key, version)
  );
  CREATE INDEX idx_variants_generation_id ON prompt_variants(generation_id);
  CREATE INDEX idx_variants_active ON prompt_variants(generation_id, template_key, is_active) WHERE is_active = TRUE;
  ```

- [ ] Table `prompt_variant_history` (audit log)
  ```sql
  CREATE TABLE prompt_variant_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    variant_id UUID NOT NULL REFERENCES prompt_variants(id),
    action VARCHAR(50) NOT NULL,         -- 'created', 'updated', 'activated', 'deactivated'
    old_content TEXT,
    new_content TEXT,
    changed_by VARCHAR(255),
    changed_at TIMESTAMP DEFAULT NOW(),
    change_reason TEXT
  );
  CREATE INDEX idx_history_variant_id ON prompt_variant_history(variant_id);
  ```

### 5.2 Version Management Rules

```
┌─────────────────────────────────────────────────────────────────┐
│                    VERSION MANAGEMENT                            │
│                                                                  │
│  • Mỗi variant có version number (1, 2, 3, ...)                 │
│  • Chỉ 1 version được đánh dấu is_active = TRUE                 │
│  • Khi update: tạo version mới, deactivate version cũ           │
│  • Không bao giờ DELETE, chỉ deactivate                         │
│  • Có thể rollback về version cũ bằng cách activate lại         │
│                                                                  │
│  Example:                                                        │
│  ┌──────────┬─────────┬───────────┐                             │
│  │ template │ version │ is_active │                             │
│  ├──────────┼─────────┼───────────┤                             │
│  │ concise  │    1    │   FALSE   │  ← old                      │
│  │ concise  │    2    │   FALSE   │  ← old                      │
│  │ concise  │    3    │   TRUE    │  ← current active           │
│  └──────────┴─────────┴───────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

- [ ] Migration scripts (Alembic)

---

## 6. Input Schema (từ Orchestrator)

### 6.1 Generate Request
```json
{
  "request_id": "uuid",
  "user_id": "user_123",
  "agent_instruction": "You are a customer support agent...",
  "mode": "auto_generate",
  "template_keys": ["concise", "detailed", "step_by_step"],  // user chọn templates
  "model_params": {
    "temperature": 0.7,
    "top_p": 0.9
  }
}
```

### 6.2 Import Request (Custom YAML)
```json
{
  "request_id": "uuid",
  "user_id": "user_123",
  "mode": "custom_import",
  "custom_config_path": "s3://prompt-configs/user_123/config.yaml"
}
```

---

## 7. API Endpoints

```
# Health & Info
GET    /health                                       # Health check
GET    /info                                         # Service info

# Templates (Read-only for users)
GET    /api/v1/templates                             # List all available templates
GET    /api/v1/templates/{key}                       # Get template detail

# Prompt Operations (called by Orchestrator)
POST   /api/v1/prompts/generate                      # Generate variants using selected templates

# Generations (CRUD)
GET    /api/v1/generations                           # List generations by user_id
GET    /api/v1/generations/{id}                      # Get generation detail
GET    /api/v1/generations/{id}/variants             # Get active variants of a generation
DELETE /api/v1/generations/{id}                      # Soft delete generation

# Variants & Versioning
GET    /api/v1/variants/{id}                         # Get variant detail (active version)
GET    /api/v1/variants/{id}/versions                # List all versions of a variant
GET    /api/v1/variants/{id}/versions/{version}      # Get specific version
PUT    /api/v1/variants/{id}                         # Update variant (creates new version)
POST   /api/v1/variants/{id}/rollback                # Rollback to specific version
GET    /api/v1/variants/{id}/history                 # Get change history

# Search (Phase 5)
GET    /api/v1/prompts/search                        # Search generated prompts
```

> **Note**:
> - `user_id` được truyền trong request body/query từ Orchestrator
> - Templates là read-only, user không thể modify
> - Variants support versioning: update tạo version mới, có thể rollback

---

## 8. Message Queue (NATS)

### Subscribe (nhận jobs từ Orchestrator)
- [ ] `prompt.generate` - request generate variants
- [ ] `prompt.import` - request import custom config

### Publish (gửi results về Orchestrator)
- [ ] `prompt.completed` - job hoàn thành, kèm variant IDs
- [ ] `prompt.failed` - job thất bại, kèm error details

### Message Format
```json
// Request (from Orchestrator)
{
  "request_id": "uuid",
  "user_id": "user_123",
  "payload": { ... }
}

// Response (to Orchestrator)
{
  "request_id": "uuid",
  "status": "completed" | "failed",
  "data": {
    "prompt_id": "uuid",
    "variant_ids": ["uuid1", "uuid2", ...]
  },
  "error": null | { "code": "...", "message": "..." }
}
```

---

## 9. LLM Integration

- [ ] Abstract `LLMClient` interface
- [ ] `OpenAIClient` implementation
- [ ] `AnthropicClient` implementation
- [ ] Factory pattern để chọn provider
- [ ] Retry logic với exponential backoff
- [ ] Cost tracking per request (lưu vào metadata)

### Generate Prompt Template
```
Given the following agent instruction, generate {n} different prompt variants.
Each variant should have a different style/approach.

Agent Instruction:
{agent_instruction}

Generate variants with these styles:
1. Concise - Brief and to the point
2. Detailed - Comprehensive with examples
3. Step-by-step - Reasoning approach
4. Few-shot - Include example Q&A pairs

Output as JSON array...
```

---

## 10. Core Services

### 10.1 TemplateService (reads from CODE)
- [ ] `list_templates()` - trả về tất cả templates từ registry (code)
- [ ] `get_template(key)` - trả về template detail từ registry (code)
- [ ] `get_strategy(key)` - trả về strategy instance để generate

### 10.2 PromptService (writes to DATABASE)
- [ ] `generate_variants(request)` - dùng strategies để generate, lưu vào DB
- [ ] `get_generation(id, user_id)` - get từ DB với ownership check
- [ ] `list_generations(user_id)` - list từ DB
- [ ] `delete_generation(id, user_id)` - soft delete trong DB

### 10.3 VariantService (writes to DATABASE)
- [ ] `get_variant(id, user_id)` - get active version từ DB
- [ ] `get_variant_version(id, version)` - get specific version từ DB
- [ ] `list_versions(variant_id)` - list tất cả versions từ DB
- [ ] `update_variant(id, user_id, content, reason)` - tạo version mới trong DB
- [ ] `rollback_variant(id, user_id, target_version, reason)` - rollback trong DB
- [ ] `get_history(variant_id)` - get audit log từ DB

### 10.4 LLMService
- [ ] `generate(prompt, model_params)` - gọi LLM provider
- [ ] `parse_response(response)` - extract content từ response

---

## 11. Validation & Error Handling

- [ ] Pydantic schemas cho input validation
- [ ] Custom exceptions (`PromptNotFoundError`, `InvalidConfigError`, etc.)
- [ ] Error response format chuẩn
  ```json
  {
    "error": {
      "code": "PROMPT_NOT_FOUND",
      "message": "Prompt with id xxx not found",
      "details": {}
    }
  }
  ```
- [ ] Structured logging (JSON format)

---

## 12. Testing

- [ ] Unit tests cho services
- [ ] Mock tests cho LLM calls
- [ ] Integration tests với test database
- [ ] API endpoint tests
- [ ] NATS message handler tests

---

## 13. Observability

- [ ] `/health` endpoint (DB connection check)
- [ ] `/metrics` endpoint (Prometheus format)
- [ ] Structured logging với request_id correlation
- [ ] Log levels: DEBUG, INFO, WARNING, ERROR

---

## 14. Environment Variables

```env
# Service
SERVICE_NAME=prompt-service
SERVICE_PORT=8080
LOG_LEVEL=INFO

# PostgreSQL (shared)
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=llmops

# NATS (shared)
NATS_URL=nats://nats:4222

# Elasticsearch (shared) - Phase 5
ELASTICSEARCH_URL=http://elasticsearch:9200

# LLM Providers
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
DEFAULT_LLM_PROVIDER=openai
```

---

## 15. File Structure

```
prompt-service/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Settings (pydantic-settings)
│   ├── dependencies.py         # DI container
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── health.py       # /health, /info
│   │   │   ├── templates.py    # /api/v1/templates/*
│   │   │   ├── generations.py  # /api/v1/generations/*
│   │   │   └── variants.py     # /api/v1/variants/* (versioning)
│   │   └── errors.py           # Error handlers
│   │
│   ├── templates/              # Factory Strategy Pattern
│   │   ├── __init__.py
│   │   ├── base.py             # Abstract PromptStrategy
│   │   ├── registry.py         # TEMPLATE_REGISTRY
│   │   ├── concise.py          # ConciseStrategy
│   │   ├── detailed.py         # DetailedStrategy
│   │   ├── step_by_step.py     # StepByStepStrategy
│   │   └── few_shot.py         # FewShotStrategy
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── template_service.py # Template listing & retrieval
│   │   ├── prompt_service.py   # Generation business logic
│   │   ├── variant_service.py  # Version management
│   │   └── llm_service.py      # LLM integration
│   │
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── generation_repository.py
│   │   ├── variant_repository.py
│   │   └── history_repository.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py         # SQLAlchemy models
│   │   └── schemas.py          # Pydantic schemas
│   │
│   ├── queue/
│   │   ├── __init__.py
│   │   └── nats_handler.py     # NATS subscribe/publish
│   │
│   └── llm/
│       ├── __init__.py
│       ├── base.py             # Abstract LLMClient
│       ├── openai_client.py
│       └── anthropic_client.py
│
├── migrations/
│   ├── env.py
│   └── versions/
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_templates.py
│   ├── test_prompt_service.py
│   ├── test_variant_service.py
│   └── test_api.py
│
├── Dockerfile
├── requirements.txt
├── .env.example
├── alembic.ini
└── README.md
```

---

## 16. Implementation Phases

### Phase 1: Foundation
- [ ] Project setup (structure, configs, Dockerfile)
- [ ] Template strategies (Factory Pattern)
- [ ] Template API endpoints (list, get)
- [ ] Database models & migrations (với versioning schema)
- [ ] Health check endpoint

### Phase 2: Core Features
- [ ] LLM integration (OpenAI)
- [ ] `/generate` endpoint - generate variants using selected templates
- [ ] Generation CRUD endpoints

### Phase 3: Version Management
- [ ] VariantService implementation
- [ ] Version listing & retrieval endpoints
- [ ] Update variant (create new version)
- [ ] Rollback functionality
- [ ] History/audit log endpoints

### Phase 4: Message Queue
- [ ] NATS connection setup
- [ ] Subscribe handlers
- [ ] Publish results

### Phase 5: Polish
- [ ] Add Anthropic support
- [ ] Input validation
- [ ] Error handling
- [ ] Logging

### Phase 6: Search & Observability
- [ ] Elasticsearch integration
- [ ] Search endpoint
- [ ] Metrics endpoint
- [ ] Comprehensive tests
