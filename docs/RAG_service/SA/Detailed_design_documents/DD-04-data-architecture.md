# Detailed Design — Data Architecture & Infrastructure

**Document ID:** DD-04
**Version:** 1.0
**Last Updated:** 2026-02-02
**Author:** Solution Architect Team

---

## Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-02 | SA Team | Initial version |

---

## Table of Contents

- [1. Storage Overview](#1-storage-overview)
- [2. PostgreSQL Schema](#2-postgresql-schema)
  - [2.1 User Management Tables](#21-user-management-tables)
  - [2.2 RAG Data Tables](#22-rag-data-tables)
  - [2.3 Pipeline Tables](#23-pipeline-tables)
  - [2.4 Audit & System Tables](#24-audit--system-tables)
  - [2.5 Indexes & Performance](#25-indexes--performance)
- [3. Milvus Schema](#3-milvus-schema)
  - [3.1 Collection Design](#31-collection-design)
  - [3.2 Partition Strategy](#32-partition-strategy)
  - [3.3 Index Configuration](#33-index-configuration)
- [4. Elasticsearch Schema](#4-elasticsearch-schema)
  - [4.1 Index Mapping](#41-index-mapping)
  - [4.2 Analyzer Configuration](#42-analyzer-configuration)
  - [4.3 Index Settings](#43-index-settings)
- [5. MinIO Object Storage](#5-minio-object-storage)
  - [5.1 Bucket Structure](#51-bucket-structure)
  - [5.2 Naming Convention](#52-naming-convention)
  - [5.3 Lifecycle Rules](#53-lifecycle-rules)
- [6. Redis Caching Architecture](#6-redis-caching-architecture)
  - [6.1 Cache Types](#61-cache-types)
  - [6.2 Key Naming Convention](#62-key-naming-convention)
  - [6.3 TTL & Invalidation](#63-ttl--invalidation)
- [7. Infrastructure & Deployment](#7-infrastructure--deployment)
  - [7.1 Docker Compose (Development)](#71-docker-compose-development)
  - [7.2 Kubernetes (Production)](#72-kubernetes-production)
  - [7.3 Resource Allocation](#73-resource-allocation)
- [8. CI/CD Pipeline](#8-cicd-pipeline)
- [9. Monitoring Stack](#9-monitoring-stack)
- [10. Dependencies](#10-dependencies)

---

## 1. Storage Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           STORAGE ARCHITECTURE                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                         PostgreSQL                                       │    │
│  │  • User Management: tenants, users, roles, groups, user_roles           │    │
│  │  • RAG Data: knowledge_bases, uploaded_documents, chunks                │    │
│  │  • Pipeline: ingestion_pipelines, retrieval_pipelines, pipeline_runs    │    │
│  │  • System: audit_logs, sessions, kb_access                              │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                         Milvus (Vector DB)                               │    │
│  │  • Collections per KB: kb_{kb_id}_vectors                               │    │
│  │  • Fields: chunk_id, embedding, document_id, is_active, permissions     │    │
│  │  • Index: AUTOINDEX (HNSW), metric: COSINE                              │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                      Elasticsearch (Fulltext)                            │    │
│  │  • Index per KB: kb_{kb_id}_fulltext                                    │    │
│  │  • Fields: chunk_id, content, document_id, is_active, permissions       │    │
│  │  • Analyzer: vietnamese (ICU), standard                                  │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                         MinIO (Object Storage)                           │    │
│  │  • Bucket: rag-storage                                                  │    │
│  │  • Path: {tenant_id}/{kb_id}/documents/{doc_id}.{ext}                   │    │
│  │  • SSoT for raw documents                                               │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                         Redis (Cache + Queue)                            │    │
│  │  • Session: session:{session_id}                                        │    │
│  │  • Semantic cache: cache:semantic:{hash}                                │    │
│  │  • Embedding cache: cache:embed:{hash}                                  │    │
│  │  • Rate limit: ratelimit:{tenant_id}:{endpoint}                         │    │
│  │  • Queues: rag:ingestion, rag:retrieval (Redis Streams)                 │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. PostgreSQL Schema

### 2.1 User Management Tables

```sql
-- ============================================
-- TENANTS
-- ============================================
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'deleted')),
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_tenants_slug ON tenants(slug);
CREATE INDEX idx_tenants_status ON tenants(status);

-- ============================================
-- USERS
-- ============================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255),
    full_name VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(500),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'pending')),
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_email_per_tenant UNIQUE(tenant_id, email)
);

CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_email ON users(tenant_id, email);
CREATE INDEX idx_users_status ON users(status);

-- ============================================
-- ROLES
-- ============================================
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    permissions JSONB NOT NULL DEFAULT '{}',
    is_system_role BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_role_per_tenant UNIQUE(tenant_id, name)
);

-- System roles (tenant_id = NULL means global)
INSERT INTO roles (id, tenant_id, name, permissions, is_system_role) VALUES
    ('00000000-0000-0000-0000-000000000001', NULL, 'admin', '{"all": true}', TRUE),
    ('00000000-0000-0000-0000-000000000002', NULL, 'tenant_admin', '{"tenant.manage": true}', TRUE),
    ('00000000-0000-0000-0000-000000000003', NULL, 'kb_builder', '{"kb.create": true, "kb.manage": true}', TRUE),
    ('00000000-0000-0000-0000-000000000004', NULL, 'contributor', '{"doc.upload": true}', TRUE),
    ('00000000-0000-0000-0000-000000000005', NULL, 'viewer', '{"kb.query": true}', TRUE);

-- ============================================
-- USER ROLES (Many-to-Many with Scope)
-- ============================================
CREATE TABLE user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    scope_type VARCHAR(50) NOT NULL CHECK (scope_type IN ('global', 'tenant', 'kb')),
    scope_id UUID,  -- NULL for global, tenant_id for tenant scope, kb_id for KB scope
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_user_role_scope UNIQUE(user_id, role_id, scope_type, scope_id)
);

CREATE INDEX idx_user_roles_user ON user_roles(user_id);
CREATE INDEX idx_user_roles_scope ON user_roles(scope_type, scope_id);

-- ============================================
-- GROUPS
-- ============================================
CREATE TABLE groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_group_per_tenant UNIQUE(tenant_id, name)
);

CREATE INDEX idx_groups_tenant ON groups(tenant_id);

-- ============================================
-- USER GROUPS (Many-to-Many)
-- ============================================
CREATE TABLE user_groups (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    group_id UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    added_at TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (user_id, group_id)
);

CREATE INDEX idx_user_groups_group ON user_groups(group_id);
```

### 2.2 RAG Data Tables

```sql
-- ============================================
-- KNOWLEDGE BASES
-- ============================================
CREATE TYPE kb_permission_type AS ENUM ('public', 'private', 'custom');

CREATE TABLE knowledge_bases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    permission_type kb_permission_type DEFAULT 'private',
    owner_id UUID NOT NULL REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'processing')),

    -- Stats (denormalized for performance)
    document_count INT DEFAULT 0,
    chunk_count INT DEFAULT 0,
    total_size_bytes BIGINT DEFAULT 0,

    -- Config references
    active_ingestion_pipeline_id UUID,
    active_retrieval_pipeline_id UUID,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_kb_tenant ON knowledge_bases(tenant_id);
CREATE INDEX idx_kb_owner ON knowledge_bases(owner_id);
CREATE INDEX idx_kb_status ON knowledge_bases(status);

-- ============================================
-- KB ACCESS CONTROL
-- ============================================
CREATE TABLE kb_access (
    kb_id UUID NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    entity_type VARCHAR(20) NOT NULL CHECK (entity_type IN ('user', 'group')),
    entity_id UUID NOT NULL,
    permission_level VARCHAR(20) NOT NULL CHECK (permission_level IN ('viewer', 'contributor', 'builder')),
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (kb_id, entity_type, entity_id)
);

CREATE INDEX idx_kb_access_entity ON kb_access(entity_type, entity_id);

-- ============================================
-- UPLOADED DOCUMENTS
-- ============================================
CREATE TYPE doc_permission_type AS ENUM ('inherit', 'private', 'custom');
CREATE TYPE doc_status AS ENUM ('pending', 'processing', 'active', 'error', 'inactive');

CREATE TABLE uploaded_documents (
    -- ID is hash(kb_id + ":" + filename) for deterministic conflict detection
    id VARCHAR(64) PRIMARY KEY,
    kb_id UUID NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    filename VARCHAR(500) NOT NULL,
    minio_path VARCHAR(1000) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    content_hash VARCHAR(64),  -- SHA256 of file content

    -- Permissions
    permission_type doc_permission_type DEFAULT 'inherit',
    owner_id UUID NOT NULL REFERENCES users(id),
    allowed_user_ids UUID[] DEFAULT '{}',
    allowed_group_ids UUID[] DEFAULT '{}',

    -- Lifecycle
    status doc_status DEFAULT 'pending',
    is_active BOOLEAN DEFAULT TRUE,
    deleted_at TIMESTAMP,
    deleted_by UUID REFERENCES users(id),

    -- Processing info
    chunk_count INT DEFAULT 0,
    ingested_with_config_id UUID,
    processing_error TEXT,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_filename_per_kb UNIQUE(kb_id, filename)
);

CREATE INDEX idx_docs_kb ON uploaded_documents(kb_id);
CREATE INDEX idx_docs_status ON uploaded_documents(status);
CREATE INDEX idx_docs_is_active ON uploaded_documents(is_active);
CREATE INDEX idx_docs_owner ON uploaded_documents(owner_id);
CREATE INDEX idx_docs_deleted ON uploaded_documents(deleted_at) WHERE deleted_at IS NOT NULL;

-- ============================================
-- CHUNKS
-- ============================================
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id VARCHAR(64) NOT NULL REFERENCES uploaded_documents(id) ON DELETE CASCADE,
    kb_id UUID NOT NULL REFERENCES knowledge_bases(id),
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,

    -- Position in original document
    start_char INT,
    end_char INT,
    page_number INT,

    -- Processing metadata
    content_type VARCHAR(50) DEFAULT 'text',  -- text, table, code
    chunker_strategy VARCHAR(50),
    token_count INT,

    -- Permissions (denormalized from document for query performance)
    permission_type doc_permission_type DEFAULT 'inherit',
    owner_id UUID NOT NULL,
    is_public BOOLEAN DEFAULT FALSE,
    allowed_user_ids UUID[] DEFAULT '{}',
    allowed_group_ids UUID[] DEFAULT '{}',

    -- Lifecycle
    is_active BOOLEAN DEFAULT TRUE,

    -- Vectors reference (for lineage)
    milvus_id VARCHAR(100),
    es_id VARCHAR(100),

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_chunks_document ON chunks(document_id);
CREATE INDEX idx_chunks_kb ON chunks(kb_id);
CREATE INDEX idx_chunks_is_active ON chunks(is_active);
CREATE INDEX idx_chunks_owner ON chunks(owner_id);
```

### 2.3 Pipeline Tables

```sql
-- ============================================
-- PIPELINE CONFIGS
-- ============================================
CREATE TABLE pipeline_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kb_id UUID NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    pipeline_type VARCHAR(20) NOT NULL CHECK (pipeline_type IN ('ingestion', 'retrieval')),
    name VARCHAR(255) NOT NULL,
    version INT NOT NULL DEFAULT 1,
    is_active BOOLEAN DEFAULT FALSE,

    -- Denormalized key fields for quick access
    embedding_model VARCHAR(100),
    embedding_dimension INT,
    search_type VARCHAR(20),

    -- Full config as JSONB
    config JSONB NOT NULL,

    -- Migration tracking
    requires_reindex BOOLEAN DEFAULT FALSE,
    reindex_started_at TIMESTAMP,
    reindex_completed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    created_by UUID REFERENCES users(id),

    CONSTRAINT unique_pipeline_version UNIQUE(kb_id, pipeline_type, version)
);

CREATE INDEX idx_pipeline_kb ON pipeline_configs(kb_id);
CREATE INDEX idx_pipeline_active ON pipeline_configs(kb_id, pipeline_type, is_active) WHERE is_active = TRUE;
CREATE INDEX idx_pipeline_embedding ON pipeline_configs(embedding_model);

-- ============================================
-- PIPELINE RUNS (Job Tracking)
-- ============================================
CREATE TYPE job_status AS ENUM ('pending', 'processing', 'completed', 'error', 'cancelled');

CREATE TABLE pipeline_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id VARCHAR(100) UNIQUE NOT NULL,
    pipeline_type VARCHAR(20) NOT NULL CHECK (pipeline_type IN ('ingestion', 'retrieval')),
    pipeline_config_id UUID REFERENCES pipeline_configs(id),
    kb_id UUID NOT NULL REFERENCES knowledge_bases(id),

    -- Job details
    document_ids VARCHAR(64)[],  -- For ingestion
    query TEXT,                   -- For retrieval
    user_id UUID REFERENCES users(id),

    -- Config snapshot
    config_snapshot JSONB,

    -- Progress
    status job_status DEFAULT 'pending',
    total_items INT,
    processed_items INT DEFAULT 0,
    failed_items INT DEFAULT 0,

    -- Timing
    queued_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- Results
    result JSONB,
    error_message TEXT,
    error_details JSONB,

    -- Retry tracking
    retry_count INT DEFAULT 0,
    last_retry_at TIMESTAMP
);

CREATE INDEX idx_pipeline_runs_status ON pipeline_runs(status);
CREATE INDEX idx_pipeline_runs_kb ON pipeline_runs(kb_id);
CREATE INDEX idx_pipeline_runs_job ON pipeline_runs(job_id);
CREATE INDEX idx_pipeline_runs_queued ON pipeline_runs(queued_at);
```

### 2.4 Audit & System Tables

```sql
-- ============================================
-- AUDIT LOGS
-- ============================================
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),

    -- Event identification
    event_type VARCHAR(50) NOT NULL,
    event_category VARCHAR(30) NOT NULL,
    event_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Actor
    actor_id UUID REFERENCES users(id),
    actor_type VARCHAR(20) NOT NULL CHECK (actor_type IN ('user', 'system', 'cron', 'api_key')),
    actor_ip INET,
    actor_user_agent TEXT,

    -- Target
    target_type VARCHAR(50),
    target_id VARCHAR(100),

    -- Event details
    action VARCHAR(50) NOT NULL,
    old_value JSONB,
    new_value JSONB,
    metadata JSONB,

    -- Immutability
    checksum VARCHAR(64) NOT NULL
);

-- Partitioning by month for performance
CREATE INDEX idx_audit_tenant_time ON audit_logs(tenant_id, event_timestamp);
CREATE INDEX idx_audit_actor ON audit_logs(actor_id, event_timestamp);
CREATE INDEX idx_audit_target ON audit_logs(target_type, target_id);
CREATE INDEX idx_audit_event_type ON audit_logs(event_type, event_timestamp);

-- ============================================
-- SESSIONS
-- ============================================
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    refresh_token_hash VARCHAR(64),
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_activity_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_token ON sessions(token_hash);
CREATE INDEX idx_sessions_expires ON sessions(expires_at);

-- ============================================
-- QUERY RESPONSES (for lineage tracking)
-- ============================================
CREATE TABLE query_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_id VARCHAR(100) NOT NULL,
    kb_id UUID NOT NULL REFERENCES knowledge_bases(id),
    user_id UUID REFERENCES users(id),

    query_text TEXT NOT NULL,
    processed_query TEXT,
    answer_text TEXT,

    -- Lineage
    source_chunks UUID[] NOT NULL,  -- chunk IDs used
    retrieval_scores JSONB,         -- chunk_id -> score
    rerank_scores JSONB,

    -- LLM details
    llm_model VARCHAR(100),
    prompt_tokens INT,
    completion_tokens INT,
    latency_ms INT,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_query_responses_kb ON query_responses(kb_id);
CREATE INDEX idx_query_responses_user ON query_responses(user_id);
CREATE INDEX idx_query_responses_time ON query_responses(created_at);
```

### 2.5 Indexes & Performance

**Composite Indexes for Common Queries:**

```sql
-- Fast lookup: active documents in a KB
CREATE INDEX idx_docs_kb_active ON uploaded_documents(kb_id, is_active) WHERE is_active = TRUE;

-- Fast lookup: chunks with permission filter
CREATE INDEX idx_chunks_permission ON chunks(kb_id, is_active, permission_type);

-- Fast lookup: user's accessible KBs
CREATE INDEX idx_kb_access_lookup ON kb_access(entity_id, entity_type);

-- Fast lookup: pending jobs
CREATE INDEX idx_jobs_pending ON pipeline_runs(status, queued_at) WHERE status = 'pending';
```

**GIN Indexes for JSONB:**

```sql
-- Search within pipeline config
CREATE INDEX idx_pipeline_config_gin ON pipeline_configs USING GIN (config);

-- Search within audit metadata
CREATE INDEX idx_audit_metadata_gin ON audit_logs USING GIN (metadata);
```

---

## 3. Milvus Schema

### 3.1 Collection Design

**Collection per Knowledge Base:**

```python
from pymilvus import CollectionSchema, FieldSchema, DataType

def create_kb_collection(kb_id: str, dimension: int = 3072) -> Collection:
    """Create Milvus collection for a Knowledge Base."""

    fields = [
        FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=100, is_primary=True),
        FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dimension),

        # Permission fields for filtering
        FieldSchema(name="is_active", dtype=DataType.BOOL),
        FieldSchema(name="permission_type", dtype=DataType.VARCHAR, max_length=20),
        FieldSchema(name="owner_id", dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="is_public", dtype=DataType.BOOL),

        # Metadata for filtering
        FieldSchema(name="content_type", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="created_at", dtype=DataType.INT64),  # Unix timestamp
    ]

    schema = CollectionSchema(
        fields=fields,
        description=f"Vector collection for KB {kb_id}"
    )

    collection = Collection(
        name=f"kb_{kb_id.replace('-', '_')}",
        schema=schema
    )

    return collection
```

### 3.2 Partition Strategy

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         MILVUS PARTITION STRATEGY                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Option 1: Collection per KB (Current)                                          │
│  ┌────────────────────────────────────────────────────────────────────────┐     │
│  │  Collection: kb_abc123                                                  │     │
│  │  └── All vectors for KB in one collection                              │     │
│  │                                                                         │     │
│  │  Collection: kb_def456                                                  │     │
│  │  └── All vectors for another KB                                        │     │
│  └────────────────────────────────────────────────────────────────────────┘     │
│                                                                                  │
│  Pros: Clean isolation, easy to drop entire KB                                  │
│  Cons: Many collections if many KBs                                             │
│                                                                                  │
│  ──────────────────────────────────────────────────────────────────────────      │
│                                                                                  │
│  Option 2: Partition by Tenant (Alternative for scale)                          │
│  ┌────────────────────────────────────────────────────────────────────────┐     │
│  │  Collection: rag_vectors                                                │     │
│  │  ├── Partition: tenant_001                                             │     │
│  │  │   └── All KBs for tenant 001                                        │     │
│  │  ├── Partition: tenant_002                                             │     │
│  │  │   └── All KBs for tenant 002                                        │     │
│  └────────────────────────────────────────────────────────────────────────┘     │
│                                                                                  │
│  Pros: Fewer collections, partition pruning for tenant isolation               │
│  Cons: Need additional kb_id filter                                             │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Index Configuration

```python
index_params = {
    "index_type": "AUTOINDEX",  # Milvus auto-selects best index
    "metric_type": "COSINE",
    "params": {}
}

# Alternative: Manual HNSW configuration
hnsw_params = {
    "index_type": "HNSW",
    "metric_type": "COSINE",
    "params": {
        "M": 16,              # Max connections per node
        "efConstruction": 200  # Build-time accuracy
    }
}

# Search params
search_params = {
    "metric_type": "COSINE",
    "params": {
        "ef": 100  # Search-time accuracy (higher = more accurate, slower)
    }
}
```

---

## 4. Elasticsearch Schema

### 4.1 Index Mapping

```json
{
  "mappings": {
    "properties": {
      "chunk_id": {
        "type": "keyword"
      },
      "document_id": {
        "type": "keyword"
      },
      "kb_id": {
        "type": "keyword"
      },
      "content": {
        "type": "text",
        "analyzer": "vietnamese_analyzer",
        "search_analyzer": "vietnamese_search_analyzer"
      },
      "content_type": {
        "type": "keyword"
      },
      "is_active": {
        "type": "boolean"
      },
      "permission_type": {
        "type": "keyword"
      },
      "owner_id": {
        "type": "keyword"
      },
      "is_public": {
        "type": "boolean"
      },
      "allowed_user_ids": {
        "type": "keyword"
      },
      "allowed_group_ids": {
        "type": "keyword"
      },
      "created_at": {
        "type": "date"
      },
      "metadata": {
        "type": "object",
        "enabled": false
      }
    }
  }
}
```

### 4.2 Analyzer Configuration

```json
{
  "settings": {
    "analysis": {
      "analyzer": {
        "vietnamese_analyzer": {
          "type": "custom",
          "tokenizer": "icu_tokenizer",
          "filter": [
            "lowercase",
            "icu_folding",
            "vietnamese_stop"
          ]
        },
        "vietnamese_search_analyzer": {
          "type": "custom",
          "tokenizer": "icu_tokenizer",
          "filter": [
            "lowercase",
            "icu_folding"
          ]
        }
      },
      "filter": {
        "vietnamese_stop": {
          "type": "stop",
          "stopwords": ["và", "của", "là", "có", "cho", "được", "này", "với", "các", "trong"]
        }
      }
    }
  }
}
```

### 4.3 Index Settings

```json
{
  "settings": {
    "number_of_shards": 2,
    "number_of_replicas": 1,
    "refresh_interval": "1s",
    "max_result_window": 10000,
    "index.mapping.total_fields.limit": 2000
  }
}
```

---

## 5. MinIO Object Storage

### 5.1 Bucket Structure

```
rag-storage/                              # Main bucket
├── {tenant_id}/                          # Tenant isolation
│   ├── {kb_id}/                          # Knowledge Base
│   │   ├── documents/                    # Uploaded files
│   │   │   ├── {doc_id}.pdf
│   │   │   ├── {doc_id}.docx
│   │   │   └── ...
│   │   ├── processed/                    # Extracted content (optional cache)
│   │   │   └── {doc_id}.json
│   │   └── exports/                      # Export files
│   │       └── {export_id}.zip
│   └── ...
└── _system/                              # System files
    ├── models/                           # Cached model files
    └── temp/                             # Temporary processing files
```

### 5.2 Naming Convention

| Component | Format | Example |
|-----------|--------|---------|
| Tenant ID | UUID | `a1b2c3d4-e5f6-7890-abcd-ef1234567890` |
| KB ID | UUID | `b2c3d4e5-f6a7-8901-bcde-f12345678901` |
| Doc ID | hash(kb_id:filename) | `sha256_first_16_chars` |
| File Path | `{tenant}/{kb}/documents/{doc_id}.{ext}` | `abc.../def.../documents/1a2b3c.pdf` |

### 5.3 Lifecycle Rules

```python
lifecycle_rules = [
    {
        "ID": "delete-temp-files",
        "Status": "Enabled",
        "Filter": {"Prefix": "_system/temp/"},
        "Expiration": {"Days": 1}
    },
    {
        "ID": "archive-old-exports",
        "Status": "Enabled",
        "Filter": {"Prefix": "*/*/exports/"},
        "Transition": {
            "Days": 30,
            "StorageClass": "GLACIER"
        }
    },
    {
        "ID": "delete-archived-documents",
        "Status": "Enabled",
        "Filter": {
            "Prefix": "*/*/documents/",
            "Tag": {"Key": "status", "Value": "archived"}
        },
        "Expiration": {"Days": 365}
    }
]
```

---

## 6. Redis Caching Architecture

### 6.1 Cache Types

| Cache Type | Purpose | Data Structure |
|------------|---------|----------------|
| **Session** | User session data | Hash |
| **Semantic Cache** | Similar query results | String (JSON) |
| **Embedding Cache** | Query/chunk embeddings | String (binary) |
| **Retrieval Cache** | Search results | String (JSON) |
| **Rate Limit** | API rate limiting | Sorted Set |
| **Queue** | Job queues | Stream |

### 6.2 Key Naming Convention

```
# Pattern: {namespace}:{type}:{identifier}

# Sessions
session:{session_id}                    → Hash with user data

# Semantic Cache
cache:semantic:{kb_id}:{query_hash}     → JSON with answer + sources

# Embedding Cache
cache:embed:query:{text_hash}           → Binary vector
cache:embed:chunk:{chunk_id}            → Binary vector

# Retrieval Cache
cache:retrieval:{kb_id}:{query_hash}    → JSON with search results

# Rate Limiting
ratelimit:{tenant_id}:{endpoint}        → Sorted Set with timestamps

# Queue Streams
rag:ingestion                           → Stream for ingestion jobs
rag:retrieval                           → Stream for retrieval jobs

# Locks
lock:kb:{kb_id}                         → String for distributed lock
```

### 6.3 TTL & Invalidation

| Cache Type | Default TTL | Invalidation Trigger |
|------------|-------------|---------------------|
| **Session** | 24 hours | Logout, password change |
| **Semantic Cache** | 1 hour | Document update in KB |
| **Embedding Cache** | 7 days | Embedding model change |
| **Retrieval Cache** | 15 minutes | Document add/delete in KB |
| **Rate Limit** | 1 minute | Auto-expire |

**Cache Invalidation Flow:**

```python
async def invalidate_kb_cache(kb_id: str):
    """Invalidate all caches related to a KB when documents change."""

    patterns = [
        f"cache:semantic:{kb_id}:*",
        f"cache:retrieval:{kb_id}:*",
    ]

    for pattern in patterns:
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)

    # Log invalidation for debugging
    logger.info(f"Invalidated caches for KB {kb_id}")
```

---

## 7. Infrastructure & Deployment

### 7.1 Docker Compose (Development)

```yaml
version: '3.8'

services:
  # Application Services
  api:
    build: ./api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/rag
      - REDIS_URL=redis://redis:6379
      - MINIO_ENDPOINT=minio:9000
      - MILVUS_HOST=milvus
      - ES_HOST=elasticsearch
    depends_on:
      - postgres
      - redis
      - minio
      - milvus
      - elasticsearch

  ingestion-worker:
    build: ./worker
    command: python -m celery -A worker worker -Q ingestion -c 2
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/rag
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis

  retrieval-worker:
    build: ./worker
    command: python -m celery -A worker worker -Q retrieval -c 4
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/rag
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis

  # Data Layer
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: rag
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"

  milvus:
    image: milvusdb/milvus:v2.3-latest
    command: milvus run standalone
    environment:
      ETCD_USE_EMBED: "true"
    volumes:
      - milvus_data:/var/lib/milvus
    ports:
      - "19530:19530"

  elasticsearch:
    image: elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - es_data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"

volumes:
  postgres_data:
  redis_data:
  minio_data:
  milvus_data:
  es_data:
```

### 7.2 Kubernetes (Production)

```yaml
# API Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rag-api
  template:
    metadata:
      labels:
        app: rag-api
    spec:
      containers:
      - name: api
        image: rag-service/api:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "2000m"
            memory: "2Gi"
        envFrom:
        - configMapRef:
            name: rag-config
        - secretRef:
            name: rag-secrets

---
# Ingestion Worker Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ingestion-worker
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ingestion-worker
  template:
    spec:
      containers:
      - name: worker
        image: rag-service/worker:latest
        command: ["python", "-m", "celery", "-A", "worker", "worker", "-Q", "ingestion", "-c", "2"]
        resources:
          requests:
            cpu: "1000m"
            memory: "2Gi"
          limits:
            cpu: "4000m"
            memory: "8Gi"

---
# HPA for Workers
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ingestion-worker-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ingestion-worker
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: External
    external:
      metric:
        name: redis_stream_pending_messages
        selector:
          matchLabels:
            stream: rag:ingestion
      target:
        type: AverageValue
        averageValue: "100"
```

### 7.3 Resource Allocation

| Component | CPU Request | CPU Limit | Memory Request | Memory Limit |
|-----------|-------------|-----------|----------------|--------------|
| API Service | 500m | 2000m | 512Mi | 2Gi |
| Ingestion Worker | 1000m | 4000m | 2Gi | 8Gi |
| Retrieval Worker | 500m | 2000m | 1Gi | 4Gi |
| PostgreSQL | 1000m | 4000m | 2Gi | 8Gi |
| Milvus | 2000m | 8000m | 4Gi | 16Gi |
| Elasticsearch | 2000m | 4000m | 2Gi | 8Gi |
| Redis | 500m | 2000m | 1Gi | 4Gi |
| MinIO | 500m | 2000m | 1Gi | 4Gi |

---

## 8. CI/CD Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           CI/CD PIPELINE                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  Commit  │───▶│  Build   │───▶│   Test   │───▶│  Deploy  │───▶│  Deploy  │  │
│  │          │    │          │    │          │    │ Staging  │    │   Prod   │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│                                                                                  │
│  Stages:                                                                         │
│                                                                                  │
│  1. Build                                                                        │
│     • Lint (ruff, mypy)                                                         │
│     • Build Docker images                                                       │
│     • Push to registry                                                          │
│                                                                                  │
│  2. Test                                                                         │
│     • Unit tests (pytest)                                                       │
│     • Integration tests                                                         │
│     • Security scan (Trivy)                                                     │
│                                                                                  │
│  3. Deploy Staging                                                               │
│     • Apply K8s manifests                                                       │
│     • Run migrations                                                            │
│     • Smoke tests                                                               │
│                                                                                  │
│  4. Deploy Production (manual approval)                                          │
│     • Blue-green deployment                                                     │
│     • Health checks                                                             │
│     • Rollback on failure                                                       │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Monitoring Stack

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           MONITORING STACK                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                         Prometheus + Grafana                             │    │
│  │                                                                          │    │
│  │  Metrics:                                                                │    │
│  │  • CPU, Memory, Disk, Network (node_exporter)                           │    │
│  │  • Request latency, error rate (FastAPI metrics)                        │    │
│  │  • Queue depth, processing time (custom metrics)                        │    │
│  │  • Database connections, query latency (pg_exporter)                    │    │
│  │  • Cache hit rate, memory usage (redis_exporter)                        │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                         Langfuse / Phoenix (RAG Tracing)                 │    │
│  │                                                                          │    │
│  │  Traces:                                                                 │    │
│  │  • Query → Retrieval → Rerank → LLM flow                                │    │
│  │  • Token usage per request                                              │    │
│  │  • Retrieval quality metrics                                            │    │
│  │  • LLM latency breakdown                                                │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                         Alerting Rules                                   │    │
│  │                                                                          │    │
│  │  Critical:                                                               │    │
│  │  • Error rate > 5% for 5 minutes                                        │    │
│  │  • Queue depth > 1000 pending jobs                                      │    │
│  │  • Database connection pool exhausted                                   │    │
│  │  • Storage usage > 90%                                                  │    │
│  │                                                                          │    │
│  │  Warning:                                                                │    │
│  │  • P95 latency > 3s                                                     │    │
│  │  • Cache hit rate < 50%                                                 │    │
│  │  • Worker pod restarts > 3/hour                                         │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Dependencies

### Technology Stack Summary

| Component | Technology | Version |
|-----------|------------|---------|
| API Framework | FastAPI | 0.100+ |
| Database | PostgreSQL | 15+ |
| Vector DB | Milvus | 2.3+ |
| Search Engine | Elasticsearch | 8.x |
| Object Storage | MinIO | Latest |
| Cache + Queue | Redis | 7.x |
| Task Queue | Celery | 5.x |
| Container Runtime | Docker | 24+ |
| Orchestration | Kubernetes | 1.28+ |

### Cross-Document References

| Reference | Document | Section |
|-----------|----------|---------|
| Pipeline Config Schema | [DD-01-pipeline-engine.md] | Section 2: Pipeline Config Schema |
| Processing Components | [DD-02-processing-components.md] | All sections |
| Upload Handler | [DD-03-platform-services.md] | Section 2: Document Upload Handler |
| RBAC Tables | [DD-05-data-governance.md] | Section 1: Access Control |
| Audit Log Schema | [DD-05-data-governance.md] | Section 6: Audit Logging |

---

*Document Version: 1.0*
*Last Updated: 2026-02-02*
