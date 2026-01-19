# Guardrails Service - Architecture Documentation

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Component Details](#component-details)
- [Data Flow](#data-flow)
- [Design Patterns](#design-patterns)
- [Database Schema](#database-schema)
- [API Reference](#api-reference)
- [Integration Guide](#integration-guide)

---

## Overview

The Guardrails Service is a **stateless microservice** designed to generate, manage, and version guardrails for LLM applications. It provides pre-built templates and allows users to customize guardrails for their specific use cases.

### Key Characteristics

- **Stateless Design**: No user data is stored, only guardrail definitions
- **Template-Based**: Pre-built guardrail templates using Strategy pattern
- **Version Control**: Full versioning and history tracking for variants
- **Multi-Provider LLM**: Support for OpenAI, Anthropic, and Groq
- **Audit Trail**: Complete history of all changes
- **RESTful API**: Standard HTTP/JSON interface

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Applications                       │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP/JSON
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Application                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Health     │  │  Templates   │  │ Generations  │          │
│  │   Routes     │  │   Routes     │  │   Routes     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │   Variants   │  │  Guardrails  │                            │
│  │   Routes     │  │   Routes     │                            │
│  └──────────────┘  └──────────────┘                            │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Service Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Template   │  │  Guardrail   │  │   Variant    │          │
│  │   Service    │  │   Service    │  │   Service    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐                                               │
│  │     LLM      │                                               │
│  │   Service    │                                               │
│  └──────────────┘                                               │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Repository Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Generation  │  │   Variant    │  │   History    │          │
│  │  Repository  │  │  Repository  │  │  Repository  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Database Layer                                │
│                   (PostgreSQL + AsyncPG)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  guardrail_  │  │  guardrail_  │  │  guardrail_  │          │
│  │ generations  │  │  variants    │  │  variant_    │          │
│  │              │  │              │  │  history     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Template Registry                             │
│                    (Code-based, No DB)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Content    │  │     PII      │  │   Factual    │          │
│  │   Safety     │  │  Protection  │  │  Accuracy    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │     Tone     │  │  Compliance  │                            │
│  │   Control    │  │              │                            │
│  └──────────────┘  └──────────────┘                            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    External Services                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │     Groq     │  │    OpenAI    │  │  Anthropic   │          │
│  │     LLM      │  │     LLM      │  │     LLM      │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### Layered Architecture

The service follows a **4-layer architecture**:

1. **API Layer** (`app/api/routes/`)
   - HTTP request handling
   - Request validation
   - Response formatting
   - Error handling

2. **Service Layer** (`app/services/`)
   - Business logic
   - Orchestration
   - Transaction management
   - Error handling

3. **Repository Layer** (`app/repositories/`)
   - Database access
   - Query execution
   - Data mapping
   - CRUD operations

4. **Model Layer** (`app/models/`)
   - Database models (SQLAlchemy)
   - Request/response schemas (Pydantic)
   - Data validation

---

## Component Details

### 1. Template System

The template system uses the **Strategy Pattern** to provide different guardrail generation strategies.

#### Base Strategy Class

```python
class GuardrailStrategy(ABC):
    name: str
    description: str
    category: str

    @abstractmethod
    def build_guardrail(self, user_context: str, **kwargs) -> str:
        pass
```

#### Template Registry (Factory Pattern)

```python
TEMPLATE_REGISTRY: Dict[str, GuardrailStrategy] = {
    "content_safety": ContentSafetyStrategy(),
    "pii_protection": PIIProtectionStrategy(),
    "factual_accuracy": FactualAccuracyStrategy(),
    "tone_control": ToneControlStrategy(),
    "compliance": ComplianceStrategy(),
}
```

#### Available Templates

| Template | Category | Purpose |
|----------|----------|---------|
| `content_safety` | safety | Prevent harmful/inappropriate content |
| `pii_protection` | security | Protect personally identifiable information |
| `factual_accuracy` | quality | Ensure accuracy, prevent hallucinations |
| `tone_control` | quality | Maintain appropriate communication style |
| `compliance` | compliance | Ensure regulatory compliance |

### 2. Service Layer

#### Template Service

**Responsibility**: Template operations (read-only, no database)

**Key Methods**:
- `list_all_templates()`: Get all available templates
- `get_template_info(key)`: Get template details
- `build_guardrail(key, context, params)`: Generate guardrail
- `preview_guardrail(key, context, params)`: Preview without saving

**Dependencies**: Template Registry

#### Guardrail Service

**Responsibility**: Guardrail generation and management

**Key Methods**:
- `generate_guardrail(request)`: Generate and save guardrail
- `get_generation(id, user_id)`: Get generation by ID
- `list_generations(user_id, filters)`: List user's generations
- `delete_generation(id, user_id)`: Delete generation
- `compare_templates(request)`: Compare multiple templates
- `batch_generate(requests)`: Bulk generation

**Dependencies**: Template Service, Generation Repository

#### Variant Service

**Responsibility**: Variant management with versioning

**Key Methods**:
- `create_variant(request)`: Create variant from generation
- `get_variant(id, user_id)`: Get variant by ID
- `list_variants(user_id, filters)`: List user's variants
- `create_new_version(id, request)`: Create new version (insert-only, no update)
- `set_variant_active(id, request)`: Activate/deactivate
- `set_variant_status(id, request)`: Change status
- `delete_variant(id, user_id)`: Delete variant
- `get_variant_history(id, user_id)`: Get change history

**Dependencies**: Variant Repository, Generation Repository, History Repository

#### LLM Service

**Responsibility**: Multi-provider LLM integration

**Key Methods**:
- `generate(prompt, provider, model, ...)`: Generate text
- `chat(messages, provider, model, ...)`: Chat completion
- `is_provider_configured(provider)`: Check if configured
- `get_configured_providers()`: List configured providers

**Supported Providers**:
- OpenAI (gpt-4o-mini)
- Anthropic (claude-3-haiku-20240307)
- Groq (llama-3.3-70b-versatile) - **Default**

### 3. Repository Layer

#### Generation Repository

**Responsibility**: CRUD for `guardrail_generations` table

**Key Methods**:
- `create(user_id, template_key, context, guardrail, ...)`: Create generation
- `get_by_id(id)`: Get by ID
- `get_by_id_and_user(id, user_id)`: Get with access control
- `list_by_user(user_id, page, filters)`: Paginated list
- `delete_by_user(id, user_id)`: Delete with access control
- `count_by_user(user_id, filters)`: Count generations
- `get_recent_by_template(user_id, key, limit)`: Recent generations

#### Variant Repository

**Responsibility**: CRUD for `guardrail_variants` table with versioning

**Key Methods**:
- `create(generation_id, user_id, name, content, ...)`: Create variant
- `get_by_id_and_user(id, user_id)`: Get with access control
- `list_by_user(user_id, page, filters)`: Paginated list with filters
- `update(variant, ...)`: **DEPRECATED** - Use insert-only versioning instead
- `set_active(variant, is_active)`: Set active state
- `set_status(variant, status)`: Change status
- `delete_by_user(id, user_id)`: Delete with access control
- `get_active_variant_for_generation(gen_id, user_id)`: Get active variant
- `list_by_generation(gen_id, user_id)`: All variants for generation

#### History Repository

**Responsibility**: Audit logging for `guardrail_variant_history` table

**Key Methods**:
- `log_creation(variant_id, user_id, content, ...)`: Log creation
- `log_update(variant_id, user_id, old, new, ...)`: Log update
- `log_activation(variant_id, user_id, activated)`: Log activation
- `log_status_change(variant_id, user_id, old, new)`: Log status change
- `get_by_variant(variant_id, page)`: Get history with pagination
- `get_latest_by_variant(variant_id, limit)`: Get recent history
- `count_by_variant(variant_id)`: Count history entries

### 4. Database Models

#### GuardrailGeneration

**Purpose**: Stores generated guardrails from templates

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| user_id | String | User identifier (indexed) |
| template_key | String | Template used (indexed) |
| user_context | Text | User-provided context |
| generated_guardrail | Text | Generated guardrail content |
| parameters | JSON | Template parameters |
| metadata | JSON | Additional metadata |
| created_at | DateTime | Creation timestamp |

**Relationships**:
- One-to-many with `GuardrailVariant`

#### GuardrailVariant

**Purpose**: User-customized guardrails with versioning

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| generation_id | UUID | Foreign key to generation |
| user_id | String | User identifier (indexed) |
| name | String | Variant name |
| description | Text | Optional description |
| guardrail_content | Text | Guardrail content |
| version | Integer | Version number (auto-increment) |
| is_active | Boolean | Active state |
| status | Enum | draft/active/archived (indexed) |
| tags | JSON | User-defined tags |
| metadata | JSON | Additional metadata |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update timestamp |

**Relationships**:
- Many-to-one with `GuardrailGeneration`
- One-to-many with `GuardrailVariantHistory`

#### GuardrailVariantHistory

**Purpose**: Audit log for all variant changes

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| variant_id | UUID | Foreign key to variant (indexed) |
| user_id | String | User identifier (indexed) |
| action | Enum | Action type (created/updated/activated/etc.) |
| old_content | Text | Previous content |
| new_content | Text | New content |
| old_version | Integer | Previous version |
| new_version | Integer | New version |
| old_status | Enum | Previous status |
| new_status | Enum | New status |
| change_summary | Text | Summary of changes |
| metadata | JSON | Additional metadata |
| created_at | DateTime | Timestamp |

**Relationships**:
- Many-to-one with `GuardrailVariant`

---

## Data Flow

### Flow 1: Generate Guardrail (Basic)

```
┌──────────┐
│  Client  │
└────┬─────┘
     │ POST /api/v1/generations
     │ {user_id, template_key, user_context, parameters}
     ▼
┌─────────────────────┐
│ Generations Router  │
└────┬────────────────┘
     │ validate request
     ▼
┌─────────────────────┐
│ Guardrail Service   │
└────┬────────────────┘
     │ validate_template_key()
     ▼
┌─────────────────────┐
│  Template Service   │
└────┬────────────────┘
     │ get_template(key)
     ▼
┌─────────────────────┐
│ Template Registry   │ (Factory)
└────┬────────────────┘
     │ return Strategy instance
     ▼
┌─────────────────────┐
│  Template Strategy  │ (e.g., ContentSafetyStrategy)
└────┬────────────────┘
     │ build_guardrail(context, parameters)
     │ return generated_guardrail
     ▼
┌─────────────────────┐
│ Guardrail Service   │
└────┬────────────────┘
     │ save to database
     ▼
┌─────────────────────┐
│Generation Repository│
└────┬────────────────┘
     │ create(user_id, template_key, content, ...)
     │ INSERT INTO guardrail_generations
     ▼
┌─────────────────────┐
│    PostgreSQL       │
└────┬────────────────┘
     │ return GuardrailGeneration
     ▼
┌─────────────────────┐
│ Guardrail Service   │
└────┬────────────────┘
     │ convert to response schema
     ▼
┌─────────────────────┐
│ Generations Router  │
└────┬────────────────┘
     │ HTTP 201 Created
     ▼
┌──────────┐
│  Client  │ receives GuardrailGenerationResponse
└──────────┘
```

### Flow 2: Create Variant with History

```
┌──────────┐
│  Client  │
└────┬─────┘
     │ POST /api/v1/variants
     │ {user_id, generation_id, name, guardrail_content}
     ▼
┌─────────────────────┐
│  Variants Router    │
└────┬────────────────┘
     │ validate request
     ▼
┌─────────────────────┐
│  Variant Service    │
└────┬────────────────┘
     │ verify generation exists
     ▼
┌─────────────────────┐
│Generation Repository│
└────┬────────────────┘
     │ get_by_id_and_user(generation_id, user_id)
     │ SELECT FROM guardrail_generations WHERE ...
     ▼
┌─────────────────────┐
│    PostgreSQL       │
└────┬────────────────┘
     │ return GuardrailGeneration
     ▼
┌─────────────────────┐
│  Variant Service    │
└────┬────────────────┘
     │ create variant
     ▼
┌─────────────────────┐
│ Variant Repository  │
└────┬────────────────┘
     │ create(generation_id, user_id, name, content, version=1)
     │ INSERT INTO guardrail_variants
     ▼
┌─────────────────────┐
│    PostgreSQL       │
└────┬────────────────┘
     │ return GuardrailVariant
     ▼
┌─────────────────────┐
│  Variant Service    │
└────┬────────────────┘
     │ log creation in history
     ▼
┌─────────────────────┐
│ History Repository  │
└────┬────────────────┘
     │ log_creation(variant_id, user_id, content, version=1)
     │ INSERT INTO guardrail_variant_history
     ▼
┌─────────────────────┐
│    PostgreSQL       │
└────┬────────────────┘
     │ return HistoryEntry
     ▼
┌─────────────────────┐
│  Variant Service    │
└────┬────────────────┘
     │ convert to response schema
     ▼
┌─────────────────────┐
│  Variants Router    │
└────┬────────────────┘
     │ HTTP 201 Created
     ▼
┌──────────┐
│  Client  │ receives GuardrailVariantResponse
└──────────┘
```

### Flow 3: Create New Version (Insert-Only Versioning)

```
┌──────────┐
│  Client  │
└────┬─────┘
     │ POST /api/v1/variants/{id}/versions
     │ {user_id, guardrail_content}
     ▼
┌─────────────────────┐
│  Variants Router    │
└────┬────────────────┘
     │ validate request
     ▼
┌─────────────────────┐
│  Variant Service    │
└────┬────────────────┘
     │ get source variant
     ▼
┌─────────────────────┐
│ Variant Repository  │
└────┬────────────────┘
     │ get_by_id_and_user(variant_id, user_id)
     │ SELECT FROM guardrail_variants WHERE ...
     ▼
┌─────────────────────┐
│    PostgreSQL       │
└────┬────────────────┘
     │ return GuardrailVariant (version=3) [UNCHANGED]
     ▼
┌─────────────────────┐
│  Variant Service    │
└────┬────────────────┘
     │ prepare new version: version=4
     │ create NEW variant (not update!)
     ▼
┌─────────────────────┐
│ Variant Repository  │
└────┬────────────────┘
     │ create(generation_id, user_id, name, content)
     │ INSERT INTO guardrail_variants (new record!)
     ▼
┌─────────────────────┐
│    PostgreSQL       │
└────┬────────────────┘
     │ return NEW GuardrailVariant (version=4)
     │ Old variant (version=3) still exists!
     ▼
┌─────────────────────┐
│  Variant Service    │
└────┬────────────────┘
     │ log creation in history
     ▼
┌─────────────────────┐
│ History Repository  │
└────┬────────────────┘
     │ log_update(variant_id, old_content, new_content,
     │            old_version=3, new_version=4)
     │ INSERT INTO guardrail_variant_history
     ▼
┌─────────────────────┐
│    PostgreSQL       │
└────┬────────────────┘
     │ return HistoryEntry
     ▼
┌─────────────────────┐
│  Variant Service    │
└────┬────────────────┘
     │ convert to response schema
     ▼
┌─────────────────────┐
│  Variants Router    │
└────┬────────────────┘
     │ HTTP 200 OK
     ▼
┌──────────┐
│  Client  │ receives GuardrailVariantResponse (version=4)
└──────────┘
```

### Flow 4: Compare Templates

```
┌──────────┐
│  Client  │
└────┬─────┘
     │ POST /api/v1/guardrails/compare
     │ {user_id, template_keys: [A, B, C], user_context}
     ▼
┌─────────────────────┐
│ Guardrails Router   │
└────┬────────────────┘
     │ validate 2-5 templates
     ▼
┌─────────────────────┐
│ Guardrail Service   │
└────┬────────────────┘
     │ for each template_key:
     │   ├─ validate_template_key(A)
     │   ├─ build_guardrail(A, context)
     │   ├─ validate_template_key(B)
     │   ├─ build_guardrail(B, context)
     │   └─ ... etc
     ▼
┌─────────────────────┐
│  Template Service   │
└────┬────────────────┘
     │ get_template(A) → build_guardrail(context)
     │ get_template(B) → build_guardrail(context)
     │ get_template(C) → build_guardrail(context)
     ▼
┌─────────────────────┐
│ Template Registry   │
└────┬────────────────┘
     │ return [Strategy A, Strategy B, Strategy C]
     ▼
┌─────────────────────┐
│ Guardrail Service   │
└────┬────────────────┘
     │ collect all results
     │ create comparison results
     ▼
┌─────────────────────┐
│ Guardrails Router   │
└────┬────────────────┘
     │ HTTP 200 OK
     ▼
┌──────────┐
│  Client  │ receives CompareTemplatesResponse with all results
└──────────┘
```

---

## Design Patterns

### 1. Factory Pattern

**Where**: Template Registry (`app/templates/registry.py`)

**Purpose**: Create guardrail strategy instances based on template key

**Implementation**:
```python
TEMPLATE_REGISTRY: Dict[str, GuardrailStrategy] = {
    "content_safety": ContentSafetyStrategy(),
    "pii_protection": PIIProtectionStrategy(),
    # ...
}

def get_template(key: str) -> GuardrailStrategy:
    if key not in TEMPLATE_REGISTRY:
        raise TemplateNotFoundError(key)
    return TEMPLATE_REGISTRY[key]
```

**Benefits**:
- Decouples template selection from template implementation
- Easy to add new templates
- Centralized template management

### 2. Strategy Pattern

**Where**: Guardrail Templates (`app/templates/`)

**Purpose**: Define family of guardrail generation algorithms

**Implementation**:
```python
class GuardrailStrategy(ABC):
    @abstractmethod
    def build_guardrail(self, user_context: str, **kwargs) -> str:
        pass

class ContentSafetyStrategy(GuardrailStrategy):
    def build_guardrail(self, user_context: str, **kwargs) -> str:
        # Content safety specific implementation
        pass
```

**Benefits**:
- Different guardrail generation algorithms are interchangeable
- Easy to add new guardrail types
- Each strategy is independent and testable

### 3. Repository Pattern

**Where**: Repository Layer (`app/repositories/`)

**Purpose**: Abstract database access logic

**Implementation**:
```python
class GenerationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id, template_key, ...) -> GuardrailGeneration:
        generation = GuardrailGeneration(...)
        self.db.add(generation)
        await self.db.commit()
        return generation
```

**Benefits**:
- Decouples business logic from data access
- Easier to test (can mock repositories)
- Centralized query logic
- Database agnostic (easier to switch databases)

### 4. Service Layer Pattern

**Where**: Service Layer (`app/services/`)

**Purpose**: Encapsulate business logic and orchestrate operations

**Implementation**:
```python
class GuardrailService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.generation_repo = GenerationRepository(db)
        self.template_service = TemplateService()

    async def generate_guardrail(self, request):
        # Business logic: validate, generate, save
        pass
```

**Benefits**:
- Keeps business logic out of API routes
- Reusable across different endpoints
- Transaction management
- Orchestrates multiple repositories

### 5. Dependency Injection

**Where**: FastAPI Dependencies (`Depends(get_db)`)

**Purpose**: Inject database sessions into routes

**Implementation**:
```python
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

@router.post("/generations")
async def create_generation(
    request: GenerateGuardrailRequest,
    db: AsyncSession = Depends(get_db),
):
    service = GuardrailService(db)
    return await service.generate_guardrail(request)
```

**Benefits**:
- Automatic session management
- Clean resource cleanup
- Easier to test (can inject mock sessions)
- Follows FastAPI best practices

---

## Database Schema

### Entity-Relationship Diagram

```
┌─────────────────────────────────────────┐
│      guardrail_generations              │
├─────────────────────────────────────────┤
│ id (UUID, PK)                           │
│ user_id (String, Indexed)               │
│ template_key (String, Indexed)          │
│ user_context (Text)                     │
│ generated_guardrail (Text)              │
│ parameters (JSON)                       │
│ metadata (JSON)                         │
│ created_at (DateTime)                   │
└────────────┬────────────────────────────┘
             │ 1
             │
             │ has many
             │
             ▼ *
┌─────────────────────────────────────────┐
│       guardrail_variants                │
├─────────────────────────────────────────┤
│ id (UUID, PK)                           │
│ generation_id (UUID, FK)                │
│ user_id (String, Indexed)               │
│ name (String)                           │
│ description (Text, Nullable)            │
│ guardrail_content (Text)                │
│ version (Integer)                       │
│ is_active (Boolean)                     │
│ status (Enum: draft/active/archived)    │
│ tags (JSON)                             │
│ metadata (JSON)                         │
│ created_at (DateTime)                   │
│ updated_at (DateTime)                   │
└────────────┬────────────────────────────┘
             │ 1
             │
             │ has many
             │
             ▼ *
┌─────────────────────────────────────────┐
│    guardrail_variant_history            │
├─────────────────────────────────────────┤
│ id (UUID, PK)                           │
│ variant_id (UUID, FK, Indexed)          │
│ user_id (String, Indexed)               │
│ action (Enum: created/updated/...)      │
│ old_content (Text, Nullable)            │
│ new_content (Text, Nullable)            │
│ old_version (Integer, Nullable)         │
│ new_version (Integer, Nullable)         │
│ old_status (Enum, Nullable)             │
│ new_status (Enum, Nullable)             │
│ change_summary (Text, Nullable)         │
│ metadata (JSON)                         │
│ created_at (DateTime)                   │
└─────────────────────────────────────────┘
```

### Cascade Behavior

- Deleting a `GuardrailGeneration` cascades to delete all associated `GuardrailVariant`s
- Deleting a `GuardrailVariant` cascades to delete all associated `GuardrailVariantHistory` entries

---

## API Reference

### Base URL

```
http://localhost:8083
```

### Endpoints Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Basic health check |
| `/health/detailed` | GET | Detailed health with DB status |
| `/api/v1/templates` | GET | List all templates |
| `/api/v1/templates/{key}` | GET | Get template details |
| `/api/v1/templates/{key}/preview` | POST | Preview template |
| `/api/v1/generations` | POST | Generate guardrail |
| `/api/v1/generations` | GET | List generations |
| `/api/v1/generations/{id}` | GET | Get generation |
| `/api/v1/generations/{id}` | DELETE | Delete generation |
| `/api/v1/variants` | POST | Create variant |
| `/api/v1/variants` | GET | List variants |
| `/api/v1/variants/{id}` | GET | Get variant |
| `/api/v1/variants/{id}/versions` | POST | Create new version |
| `/api/v1/variants/{id}/activate` | POST | Activate/deactivate |
| `/api/v1/variants/{id}/status` | POST | Change status |
| `/api/v1/variants/{id}/history` | GET | Get change history |
| `/api/v1/guardrails/compare` | POST | Compare templates |
| `/api/v1/guardrails/batch` | POST | Batch generate |

---

## Integration Guide

### Typical Usage Flow

1. **Explore Templates**
   ```bash
   GET /api/v1/templates
   ```

2. **Preview Template**
   ```bash
   POST /api/v1/templates/content_safety/preview
   {
     "user_context": "Customer support chatbot",
     "parameters": {"safety_level": "standard"}
   }
   ```

3. **Generate Guardrail**
   ```bash
   POST /api/v1/generations
   {
     "user_id": "user123",
     "template_key": "content_safety",
     "user_context": "Customer support chatbot",
     "parameters": {"safety_level": "strict"}
   }
   ```

4. **Create Variant**
   ```bash
   POST /api/v1/variants
   {
     "user_id": "user123",
     "generation_id": "gen-uuid",
     "name": "Production Rules v1",
     "status": "active"
   }
   ```

5. **Create New Version**
   ```bash
   POST /api/v1/variants/{variant-uuid}/versions
   {
     "user_id": "user123",
     "guardrail_content": "Updated rules...",
     "increment_version": true
   }
   ```

6. **View History**
   ```bash
   GET /api/v1/variants/{variant-uuid}/history?user_id=user123
   ```

### Error Handling

All endpoints return standard HTTP status codes:

- `200 OK` - Successful request
- `201 Created` - Resource created
- `204 No Content` - Successful deletion
- `400 Bad Request` - Invalid request (e.g., template not found)
- `404 Not Found` - Resource not found or access denied
- `500 Internal Server Error` - Server error

Error response format:
```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Conclusion

The Guardrails Service provides a robust, scalable solution for managing AI guardrails with:

- **Template-based generation** using Strategy and Factory patterns
- **Complete versioning** and history tracking
- **User isolation** with access control
- **Stateless design** for easy horizontal scaling
- **Clean architecture** with separation of concerns

For questions or issues, please refer to the main README.md or open an issue on GitHub.
