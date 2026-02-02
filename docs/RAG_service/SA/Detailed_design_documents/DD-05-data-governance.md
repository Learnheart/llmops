# Detailed Design — Data Governance & Compliance

**Document ID:** DD-05
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

- [1. Access Control & RBAC](#1-access-control--rbac)
  - [1.1 Role Definition](#11-role-definition)
  - [1.2 Permission Matrix](#12-permission-matrix)
  - [1.3 Permission Levels](#13-permission-levels)
  - [1.4 Query-Time Permission Filter](#14-query-time-permission-filter)
- [2. Data Lineage](#2-data-lineage)
  - [2.1 Lineage Model](#21-lineage-model)
  - [2.2 Tracking Implementation](#22-tracking-implementation)
  - [2.3 Lineage Query](#23-lineage-query)
- [3. Data Quality Control](#3-data-quality-control)
  - [3.1 Input Validation](#31-input-validation)
  - [3.2 Duplicate Detection](#32-duplicate-detection)
  - [3.3 Quality Metrics](#33-quality-metrics)
- [4. Data Lifecycle Management](#4-data-lifecycle-management)
  - [4.1 Document States](#41-document-states)
  - [4.2 State Transitions](#42-state-transitions)
  - [4.3 Soft Delete & Restore](#43-soft-delete--restore)
  - [4.4 Hard Delete Policy](#44-hard-delete-policy)
- [5. PII Detection & Masking](#5-pii-detection--masking)
  - [5.1 PII Categories](#51-pii-categories)
  - [5.2 Detection Methods](#52-detection-methods)
  - [5.3 Masking Strategies](#53-masking-strategies)
- [6. Audit Logging](#6-audit-logging)
  - [6.1 Audit Events](#61-audit-events)
  - [6.2 Log Schema](#62-log-schema)
  - [6.3 Retention Policy](#63-retention-policy)
- [7. Dependencies](#7-dependencies)

---

## 1. Access Control & RBAC

### Purpose

Định nghĩa mô hình phân quyền cho hệ thống, đảm bảo **"Ai được phép truy cập dữ liệu nào?"**

### 1.1 Role Definition

| Role | Scope | Description |
|------|-------|-------------|
| **Admin** | System | Quản lý toàn bộ hệ thống: tenants, users, system settings |
| **Tenant Admin** | Tenant | Quản lý users, groups trong tenant |
| **KB Builder** | Knowledge Base | Tạo/xóa KB, configure pipeline, upload/delete documents |
| **Contributor** | Knowledge Base | Upload documents vào KB được cấp quyền |
| **Viewer** | Knowledge Base | Chỉ được query, không được upload/delete |

### 1.2 Permission Matrix

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         PERMISSION MATRIX                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Action                    │ Admin │ Tenant │ KB      │ Contri- │ Viewer │      │
│                            │       │ Admin  │ Builder │ butor   │        │      │
│  ──────────────────────────┼───────┼────────┼─────────┼─────────┼────────┤      │
│  Create Tenant             │   ✓   │   ✗    │   ✗     │   ✗     │   ✗    │      │
│  Manage Tenant Users       │   ✓   │   ✓    │   ✗     │   ✗     │   ✗    │      │
│  Create Knowledge Base     │   ✓   │   ✓    │   ✓     │   ✗     │   ✗    │      │
│  Delete Knowledge Base     │   ✓   │   ✓    │   ✓*    │   ✗     │   ✗    │      │
│  Configure Pipeline        │   ✓   │   ✓    │   ✓     │   ✗     │   ✗    │      │
│  Upload Documents          │   ✓   │   ✓    │   ✓     │   ✓     │   ✗    │      │
│  Delete Documents          │   ✓   │   ✓    │   ✓     │   ✓**   │   ✗    │      │
│  Query Knowledge Base      │   ✓   │   ✓    │   ✓     │   ✓     │   ✓    │      │
│  View Audit Logs           │   ✓   │   ✓    │   ✗     │   ✗     │   ✗    │      │
│  Manage KB Permissions     │   ✓   │   ✓    │   ✓     │   ✗     │   ✗    │      │
│                                                                                  │
│  * KB Builder can only delete KBs they own                                      │
│  ** Contributor can only delete documents they uploaded                         │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Permission Levels

Hệ thống enforce quyền ở 3 cấp độ:

#### Level 1: Tenant Level

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         TENANT ISOLATION                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌────────────────────────┐        ┌────────────────────────┐                   │
│  │       Tenant A          │        │       Tenant B          │                   │
│  │  ┌──────────────────┐  │        │  ┌──────────────────┐  │                   │
│  │  │     KB 1         │  │        │  │     KB 3         │  │                   │
│  │  └──────────────────┘  │        │  └──────────────────┘  │                   │
│  │  ┌──────────────────┐  │        │  ┌──────────────────┐  │                   │
│  │  │     KB 2         │  │        │  │     KB 4         │  │                   │
│  │  └──────────────────┘  │        │  └──────────────────┘  │                   │
│  │                        │        │                        │                   │
│  │  Users: A1, A2, A3     │        │  Users: B1, B2         │                   │
│  └────────────────────────┘        └────────────────────────┘                   │
│                                                                                  │
│  Rule: Users trong Tenant A KHÔNG THỂ access bất kỳ data nào của Tenant B      │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Implementation:**
- Mọi query đều filter theo `tenant_id` của user
- `tenant_id` được inject từ JWT token, không thể fake
- Database indexes include `tenant_id` cho efficient filtering

#### Level 2: Knowledge Base Level

```sql
-- KB permission types
CREATE TYPE kb_permission_type AS ENUM ('public', 'private', 'custom');

-- KB access control table
CREATE TABLE kb_access (
    kb_id UUID REFERENCES knowledge_bases(id),
    entity_type VARCHAR(20) NOT NULL,  -- 'user' or 'group'
    entity_id UUID NOT NULL,
    permission_level VARCHAR(20) NOT NULL,  -- 'viewer', 'contributor', 'builder'
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (kb_id, entity_type, entity_id)
);
```

| Permission Type | Access Rule |
|-----------------|-------------|
| **public** | Tất cả users trong tenant có thể query |
| **private** | Chỉ KB owner có thể access |
| **custom** | Users/Groups được liệt kê trong `kb_access` table |

#### Level 3: Document Level

```sql
-- Document permission types
CREATE TYPE doc_permission_type AS ENUM ('inherit', 'private', 'custom');

-- Document access control
ALTER TABLE uploaded_documents ADD COLUMN permission_type doc_permission_type DEFAULT 'inherit';
ALTER TABLE uploaded_documents ADD COLUMN allowed_user_ids UUID[] DEFAULT '{}';
ALTER TABLE uploaded_documents ADD COLUMN allowed_group_ids UUID[] DEFAULT '{}';
```

| Permission Type | Behavior |
|-----------------|----------|
| **inherit** (default) | Kế thừa từ KB — ai access KB thì query được document |
| **private** | Override — chỉ document owner mới query được |
| **custom** | Override — chỉ users/groups được chỉ định |

### 1.4 Query-Time Permission Filter

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      PERMISSION FILTERING FLOW                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  User Query: "What was Q3 revenue?" to KB "finance-reports"                     │
│         │                                                                        │
│         ▼                                                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  LAYER 1: KB Permission Check (API Level)                                │    │
│  │                                                                          │    │
│  │  Check: User có quyền access KB không?                                  │    │
│  │                                                                          │    │
│  │  KB.permission_type = 'public'  → Tất cả user trong tenant OK           │    │
│  │  KB.permission_type = 'private' → Chỉ KB owner OK                       │    │
│  │  KB.permission_type = 'custom'  → Check kb_access table                 │    │
│  │                                                                          │    │
│  │  ❌ Không có quyền → 403 Forbidden (KB không hiển thị)                  │    │
│  │  ✅ Có quyền → Tiếp tục Layer 2                                         │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│         │                                                                        │
│         ▼                                                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  LAYER 2: Document Filter (Search Level - Milvus/ES)                    │    │
│  │                                                                          │    │
│  │  Filter Expression:                                                     │    │
│  │  ┌───────────────────────────────────────────────────────────────────┐  │    │
│  │  │  MUST: is_active = TRUE                                           │  │    │
│  │  └───────────────────────────────────────────────────────────────────┘  │    │
│  │                          AND                                            │    │
│  │  ┌───────────────────────────────────────────────────────────────────┐  │    │
│  │  │  Document Permission (at least one):                              │  │    │
│  │  │                                                                   │  │    │
│  │  │  • permission_type = 'inherit'  → OK (đã pass KB check)          │  │    │
│  │  │  • permission_type = 'private'  → owner_id = current_user        │  │    │
│  │  │  • permission_type = 'custom'   → user in allowed_users          │  │    │
│  │  │                                   OR user.groups ∩ allowed_groups │  │    │
│  │  └───────────────────────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│         │                                                                        │
│         ▼                                                                        │
│  Filtered Search Results (only accessible documents/chunks)                     │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Milvus Filter Expression:**

```python
def build_permission_filter(user_context: UserContext) -> str:
    """Build Milvus filter expression for permission check."""
    user_id = user_context.user_id
    group_ids = user_context.group_ids

    filters = [
        "is_active == true",
        f"(permission_type == 'inherit' or "
        f"(permission_type == 'private' and owner_id == '{user_id}') or "
        f"(permission_type == 'custom' and "
        f"('{user_id}' in allowed_user_ids or "
        f"any(g in allowed_group_ids for g in {group_ids}))))"
    ]

    return " and ".join(filters)
```

---

## 2. Data Lineage

### Purpose

Tracking nguồn gốc dữ liệu xuyên suốt pipeline, trả lời **"Dữ liệu đến từ đâu và đi qua những bước nào?"**

### 2.1 Lineage Model

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           LINEAGE MODEL                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌────────────────┐                                                              │
│  │    Document    │                                                              │
│  │    (Source)    │                                                              │
│  │                │                                                              │
│  │  • id          │                                                              │
│  │  • filename    │                                                              │
│  │  • minio_path  │                                                              │
│  │  • uploaded_by │                                                              │
│  │  • uploaded_at │                                                              │
│  │  • pipeline_   │                                                              │
│  │    config_id   │                                                              │
│  └───────┬────────┘                                                              │
│          │                                                                       │
│          │ 1:N                                                                   │
│          ▼                                                                       │
│  ┌────────────────┐                                                              │
│  │     Chunk      │                                                              │
│  │                │                                                              │
│  │  • id          │                                                              │
│  │  • document_id │  ← Reference to source document                             │
│  │  • chunk_index │                                                              │
│  │  • content     │                                                              │
│  │  • start_char  │  ← Position in original document                            │
│  │  • end_char    │                                                              │
│  │  • chunker_    │  ← Which chunker strategy used                               │
│  │    strategy    │                                                              │
│  └───────┬────────┘                                                              │
│          │                                                                       │
│          │ 1:1                                                                   │
│          ▼                                                                       │
│  ┌────────────────┐                                                              │
│  │   Embedding    │                                                              │
│  │                │                                                              │
│  │  • chunk_id    │  ← Reference to chunk                                        │
│  │  • model_name  │  ← Which embedding model used                                │
│  │  • model_ver   │                                                              │
│  │  • vector      │                                                              │
│  │  • created_at  │                                                              │
│  └───────┬────────┘                                                              │
│          │                                                                       │
│          │ Used in                                                               │
│          ▼                                                                       │
│  ┌────────────────┐                                                              │
│  │    Answer      │                                                              │
│  │   (Response)   │                                                              │
│  │                │                                                              │
│  │  • query_id    │                                                              │
│  │  • answer_text │                                                              │
│  │  • source_     │  ← List of chunk_ids used to generate answer                │
│  │    chunks[]    │                                                              │
│  │  • llm_model   │                                                              │
│  │  • created_at  │                                                              │
│  └────────────────┘                                                              │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Tracking Implementation

**Chunk-to-Document Tracking:**

```python
@dataclass
class ChunkMetadata:
    chunk_id: str
    document_id: str
    chunk_index: int
    start_char: int
    end_char: int
    chunker_strategy: str
    created_at: datetime
    pipeline_config_id: str

# Stored in PostgreSQL chunks table
# Also embedded as metadata in Milvus/ES for filtering
```

**Answer-to-Chunks Tracking:**

```python
@dataclass
class AnswerLineage:
    query_id: str
    query_text: str
    answer_text: str
    source_chunks: List[str]  # List of chunk_ids
    retrieval_scores: Dict[str, float]  # chunk_id -> relevance score
    rerank_scores: Optional[Dict[str, float]]
    llm_model: str
    prompt_tokens: int
    completion_tokens: int
    created_at: datetime
```

### 2.3 Lineage Query

**Use Case: "Câu trả lời này dựa trên tài liệu nào?"**

```sql
-- Get complete lineage for an answer
WITH answer_chunks AS (
    SELECT unnest(source_chunks) as chunk_id
    FROM query_responses
    WHERE query_id = 'query_001'
)
SELECT
    qr.query_id,
    qr.answer_text,
    c.chunk_index,
    c.content as chunk_content,
    d.filename as document_name,
    d.minio_path,
    u.full_name as uploaded_by,
    d.created_at as document_uploaded_at,
    pc.config as pipeline_config_used
FROM query_responses qr
JOIN answer_chunks ac ON true
JOIN chunks c ON c.id = ac.chunk_id
JOIN uploaded_documents d ON d.id = c.document_id
JOIN users u ON u.id = d.owner_id
JOIN pipeline_configs pc ON pc.id = d.ingested_with_config_id
WHERE qr.query_id = 'query_001';
```

**Response Format với Lineage:**

```json
{
  "query_id": "query_001",
  "answer": "Q3 revenue was $10M, representing a 15% increase...",
  "sources": [
    {
      "chunk_id": "chunk_001",
      "document": {
        "id": "doc_001",
        "filename": "Q3_Financial_Report.pdf",
        "uploaded_by": "john@company.com",
        "uploaded_at": "2026-01-15T10:00:00Z"
      },
      "excerpt": "...Q3 revenue reached $10 million...",
      "page": 5,
      "relevance_score": 0.92
    },
    {
      "chunk_id": "chunk_002",
      "document": {
        "id": "doc_002",
        "filename": "Revenue_Analysis_2025.xlsx",
        "uploaded_by": "jane@company.com",
        "uploaded_at": "2026-01-20T14:30:00Z"
      },
      "excerpt": "...year-over-year growth of 15%...",
      "relevance_score": 0.87
    }
  ],
  "pipeline_used": {
    "embedding_model": "jinaai-v3",
    "search_type": "hybrid",
    "reranker": "bge-reranker-v2",
    "llm": "gpt-4"
  }
}
```

---

## 3. Data Quality Control

### Purpose

Kiểm soát chất lượng đầu vào, trả lời **"Dữ liệu có đáng tin cậy không?"**

### 3.1 Input Validation

| Validation | Check | Action on Fail |
|------------|-------|----------------|
| **File Type** | Extension in whitelist (pdf, docx, xlsx, etc.) | Reject with error |
| **File Size** | Max 100MB per file | Reject with error |
| **MIME Type** | Magic bytes match expected type | Reject with error |
| **Malware Scan** | Optional ClamAV scan | Reject with error |
| **Content Extraction** | Parser returns non-empty text | Mark as ERROR status |
| **Character Encoding** | Valid UTF-8 | Attempt auto-fix, fail if can't |
| **Minimum Content** | At least 100 characters extracted | Mark as ERROR status |

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        INPUT VALIDATION FLOW                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  File Upload                                                                     │
│       │                                                                          │
│       ▼                                                                          │
│  ┌─────────────────┐                                                            │
│  │ File Extension  │── Check against whitelist                                  │
│  └────────┬────────┘                                                            │
│           │ ✓                                                                    │
│           ▼                                                                      │
│  ┌─────────────────┐                                                            │
│  │ File Size       │── Max 100MB                                                │
│  └────────┬────────┘                                                            │
│           │ ✓                                                                    │
│           ▼                                                                      │
│  ┌─────────────────┐                                                            │
│  │ MIME Type       │── Magic bytes verification                                 │
│  └────────┬────────┘                                                            │
│           │ ✓                                                                    │
│           ▼                                                                      │
│  ┌─────────────────┐                                                            │
│  │ Malware Scan    │── Optional, configurable per tenant                        │
│  └────────┬────────┘                                                            │
│           │ ✓                                                                    │
│           ▼                                                                      │
│  Store to MinIO, create metadata record (status = PENDING)                      │
│       │                                                                          │
│       ▼                                                                          │
│  Push to Ingestion Queue                                                         │
│       │                                                                          │
│       ▼                                                                          │
│  ┌─────────────────┐                                                            │
│  │ Content Extract │── Parser extracts text                                     │
│  └────────┬────────┘                                                            │
│           │                                                                      │
│      ┌────┴────┐                                                                 │
│      │         │                                                                 │
│  Non-empty   Empty                                                              │
│      │         │                                                                 │
│      ▼         ▼                                                                 │
│  Continue   Mark ERROR                                                          │
│  pipeline   "No extractable content"                                            │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Duplicate Detection

**Current Implementation (Filename-based):**

```sql
-- Check duplicate by filename within KB
SELECT COUNT(*) FROM uploaded_documents
WHERE kb_id = ? AND filename = ? AND is_active = TRUE;
```

| Conflict Case | Detection | Resolution Options |
|--------------|-----------|---------------------|
| Same filename in KB | Check before upload | SKIP, RENAME, REPLACE |
| Same content (hash) | Compare content_hash | Warn user, allow proceed |
| Same file across KBs | Allowed | No restriction |

**Future Enhancement (Content-based):**

```python
# Near-duplicate detection using MinHash/SimHash
def detect_near_duplicates(new_doc_text: str, kb_id: str) -> List[Document]:
    new_minhash = compute_minhash(new_doc_text)
    existing_docs = get_kb_documents(kb_id)

    duplicates = []
    for doc in existing_docs:
        similarity = minhash_similarity(new_minhash, doc.minhash)
        if similarity > 0.9:  # 90% similar
            duplicates.append(doc)

    return duplicates
```

### 3.3 Quality Metrics

| Metric | Measurement | Threshold | Action |
|--------|-------------|-----------|--------|
| **Extraction Rate** | % of documents successfully parsed | > 95% | Alert if below |
| **Empty Chunk Rate** | % of chunks with < 50 chars | < 5% | Review chunker config |
| **Encoding Errors** | Count of UTF-8 decode failures | 0 | Log and investigate |
| **Parse Latency** | P95 parsing time per document | < 30s | Scale parsers |

---

## 4. Data Lifecycle Management

### Purpose

Quản lý vòng đời của documents, trả lời **"Dữ liệu tồn tại bao lâu và qua những giai đoạn nào?"**

### 4.1 Document States

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        DOCUMENT STATE MACHINE                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│     ┌───────────┐                                                               │
│     │  PENDING  │ ── Document uploaded, waiting for processing                  │
│     └─────┬─────┘                                                               │
│           │                                                                      │
│      ┌────┴────┐                                                                 │
│      │         │                                                                 │
│   Success    Failure                                                            │
│      │         │                                                                 │
│      ▼         ▼                                                                 │
│  ┌───────┐  ┌───────┐                                                           │
│  │ACTIVE │  │ ERROR │ ── Parse failed, no extractable content                  │
│  └───┬───┘  └───────┘                                                           │
│      │                                                                           │
│      │ User deletes                                                              │
│      ▼                                                                           │
│  ┌──────────┐                                                                   │
│  │ INACTIVE │ ── Soft deleted, in Trash                                        │
│  └─────┬────┘                                                                   │
│        │                                                                         │
│   ┌────┴────┐                                                                    │
│   │         │                                                                    │
│ Restore  30 days                                                                │
│   │         │                                                                    │
│   ▼         ▼                                                                    │
│ ACTIVE   DELETED ── Hard deleted, data removed                                  │
│          (permanent)                                                             │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 State Transitions

| From | To | Trigger | Side Effects |
|------|-----|---------|--------------|
| - | PENDING | User uploads file | Create metadata record, store file in MinIO |
| PENDING | ACTIVE | Ingestion success | Update chunk_count, set status |
| PENDING | ERROR | Ingestion failure | Log error, no chunks created |
| ACTIVE | INACTIVE | User deletes | Set is_active=FALSE, deleted_at=NOW(), mark chunks inactive |
| INACTIVE | ACTIVE | User restores | Set is_active=TRUE, deleted_at=NULL, reactivate chunks |
| INACTIVE | DELETED | 30 days in trash | Hard delete from all storage |
| ERROR | PENDING | User triggers re-process | Reset status, push to queue again |

### 4.3 Soft Delete & Restore

**Soft Delete Implementation:**

```sql
-- Soft delete document
UPDATE uploaded_documents
SET
    is_active = FALSE,
    deleted_at = NOW(),
    deleted_by = :user_id
WHERE id = :document_id;

-- Also soft delete chunks
UPDATE chunks
SET is_active = FALSE
WHERE document_id = :document_id;

-- Note: DO NOT delete from Milvus/ES immediately
-- Chunks are filtered out at query time via is_active filter
```

**Restore Implementation:**

```sql
-- Restore document
UPDATE uploaded_documents
SET
    is_active = TRUE,
    deleted_at = NULL,
    deleted_by = NULL
WHERE id = :document_id;

-- Restore chunks
UPDATE chunks
SET is_active = TRUE
WHERE document_id = :document_id;

-- No re-indexing needed - vectors are still in Milvus/ES
```

### 4.4 Hard Delete Policy

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        HARD DELETE PROCESS                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Daily Cron Job: hard_delete_expired_documents                                   │
│                                                                                  │
│  1. Find documents to delete:                                                   │
│     SELECT * FROM uploaded_documents                                            │
│     WHERE is_active = FALSE                                                     │
│       AND deleted_at < NOW() - INTERVAL '30 days'                               │
│                                                                                  │
│  2. For each document:                                                          │
│     a. Delete vectors from Milvus                                               │
│        DELETE FROM collection WHERE document_id = :doc_id                       │
│                                                                                  │
│     b. Delete from Elasticsearch                                                │
│        DELETE /index/_doc WHERE document_id = :doc_id                           │
│                                                                                  │
│     c. Delete chunks from PostgreSQL                                            │
│        DELETE FROM chunks WHERE document_id = :doc_id                           │
│                                                                                  │
│     d. Delete file from MinIO                                                   │
│        s3.delete_object(bucket, minio_path)                                     │
│                                                                                  │
│     e. Delete document metadata                                                 │
│        DELETE FROM uploaded_documents WHERE id = :doc_id                        │
│                                                                                  │
│  3. Log deletion to audit_logs                                                  │
│                                                                                  │
│  Note: Raw file on MinIO có thể giữ lại thêm cho audit (configurable)          │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Retention Configuration:**

```python
@dataclass
class RetentionConfig:
    soft_delete_retention_days: int = 30  # Days before hard delete
    audit_log_retention_years: int = 7    # Years to keep audit logs
    raw_file_archive_enabled: bool = True # Keep raw files after hard delete
    raw_file_archive_days: int = 365      # Days to keep archived files
```

---

## 5. PII Detection & Masking

### Purpose

Bảo vệ thông tin cá nhân nhạy cảm, trả lời **"Dữ liệu nhạy cảm được bảo vệ như thế nào?"**

### 5.1 PII Categories

| Category | Examples | Detection Method | Default Action |
|----------|----------|------------------|----------------|
| **National ID** | CMND, CCCD (12 digits) | Regex | Mask |
| **Phone Number** | 0912345678, +84912345678 | Regex | Mask |
| **Email Address** | user@domain.com | Regex | Mask (preserve domain) |
| **Bank Account** | 16-digit numbers | Regex + context | Mask |
| **Credit Card** | Visa, Mastercard patterns | Luhn validation | Mask |
| **Address** | Street, ward, district | NER | Context-dependent |
| **Name** | Vietnamese names | NER | Context-dependent |

### 5.2 Detection Methods

**Regex-based Detection:**

```python
PII_PATTERNS = {
    "vietnam_id": r"\b\d{9}|\d{12}\b",
    "phone_vn": r"\b(0|\+84)[35789]\d{8}\b",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "bank_account": r"\b\d{10,16}\b",  # Requires context validation
    "credit_card": r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14})\b",
}
```

**NER-based Detection (Future):**

```python
from transformers import pipeline

ner_pipeline = pipeline("ner", model="VietAI/vit5-large-vietnews-segmentation")

def detect_pii_ner(text: str) -> List[PIIEntity]:
    entities = ner_pipeline(text)
    pii_entities = []

    for entity in entities:
        if entity["entity"] in ["PER", "LOC", "ORG"]:
            pii_entities.append(PIIEntity(
                type=entity["entity"],
                value=entity["word"],
                start=entity["start"],
                end=entity["end"],
                confidence=entity["score"]
            ))

    return pii_entities
```

### 5.3 Masking Strategies

| Strategy | Description | Example |
|----------|-------------|---------|
| **Full Mask** | Replace entirely with placeholder | `0912345678` → `[PHONE]` |
| **Partial Mask** | Keep first/last characters | `0912345678` → `091***5678` |
| **Hash** | Replace with hash (reversible with key) | `user@email.com` → `abc123...@email.com` |
| **Encrypt** | Encrypt and store key separately | Reversible by authorized users |
| **Remove** | Delete from indexed content | Not included in search/retrieval |

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        PII MASKING FLOW                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Extracted Text                                                                  │
│       │                                                                          │
│       ▼                                                                          │
│  ┌─────────────────┐                                                            │
│  │  PII Scanner    │── Detect PII using regex + optional NER                    │
│  └────────┬────────┘                                                            │
│           │                                                                      │
│           ▼                                                                      │
│  ┌─────────────────┐                                                            │
│  │ PII Entities    │                                                            │
│  │ Found: [        │                                                            │
│  │   {phone: 0912} │                                                            │
│  │   {email: ...}  │                                                            │
│  │ ]               │                                                            │
│  └────────┬────────┘                                                            │
│           │                                                                      │
│           ▼                                                                      │
│  ┌─────────────────┐                                                            │
│  │ Apply Masking   │── Based on tenant/KB policy                                │
│  │ Strategy        │                                                            │
│  └────────┬────────┘                                                            │
│           │                                                                      │
│           ▼                                                                      │
│  ┌─────────────────┐                                                            │
│  │ Store Original  │── In encrypted field (for authorized access)              │
│  │ Store Masked    │── In indexed content (for search/retrieval)               │
│  └─────────────────┘                                                            │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Configuration per KB:**

```json
{
  "pii_handling": {
    "enabled": true,
    "scan_on_ingest": true,
    "categories": {
      "phone": { "action": "mask", "strategy": "partial" },
      "email": { "action": "mask", "strategy": "partial" },
      "national_id": { "action": "mask", "strategy": "full" },
      "bank_account": { "action": "remove", "strategy": null },
      "name": { "action": "keep", "strategy": null }
    },
    "store_original_encrypted": true,
    "authorized_roles": ["admin", "compliance"]
  }
}
```

---

## 6. Audit Logging

### Purpose

Ghi lại mọi hành động liên quan đến dữ liệu, trả lời **"Hệ thống chứng minh compliance bằng cách nào?"**

### 6.1 Audit Events

| Event Category | Events | Logged Data |
|----------------|--------|-------------|
| **Document** | UPLOAD, DELETE, RESTORE, HARD_DELETE | document_id, user_id, action, timestamp |
| **Query** | QUERY_SUBMITTED, QUERY_COMPLETED | query_id, user_id, kb_id, query_text (optional) |
| **Permission** | GRANT_ACCESS, REVOKE_ACCESS, ROLE_CHANGE | target_entity, action, performer |
| **Config** | PIPELINE_CREATE, PIPELINE_UPDATE, KB_CREATE | config_id, old_value, new_value |
| **Auth** | LOGIN, LOGOUT, TOKEN_REFRESH, LOGIN_FAILED | user_id, ip_address, user_agent |

### 6.2 Log Schema

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),

    -- Event identification
    event_type VARCHAR(50) NOT NULL,
    event_category VARCHAR(30) NOT NULL,
    event_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Actor
    actor_id UUID REFERENCES users(id),
    actor_type VARCHAR(20) NOT NULL,  -- 'user', 'system', 'cron'
    actor_ip VARCHAR(45),
    actor_user_agent TEXT,

    -- Target
    target_type VARCHAR(50),  -- 'document', 'kb', 'user', 'pipeline'
    target_id VARCHAR(100),

    -- Event details
    action VARCHAR(50) NOT NULL,
    old_value JSONB,
    new_value JSONB,
    metadata JSONB,

    -- Immutability
    checksum VARCHAR(64) NOT NULL,  -- SHA256 of event data

    -- Indexing
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX idx_audit_tenant_time ON audit_logs(tenant_id, event_timestamp);
CREATE INDEX idx_audit_actor ON audit_logs(actor_id, event_timestamp);
CREATE INDEX idx_audit_target ON audit_logs(target_type, target_id);
CREATE INDEX idx_audit_event_type ON audit_logs(event_type);
```

**Immutability Guarantee:**

```python
def create_audit_log(event: AuditEvent) -> AuditLog:
    # Compute checksum from event data
    event_data = {
        "event_type": event.event_type,
        "actor_id": str(event.actor_id),
        "target_id": event.target_id,
        "action": event.action,
        "timestamp": event.timestamp.isoformat()
    }
    checksum = hashlib.sha256(json.dumps(event_data, sort_keys=True).encode()).hexdigest()

    log = AuditLog(
        **event.__dict__,
        checksum=checksum
    )

    # Insert only, no UPDATE/DELETE allowed on audit_logs
    db.insert(log)

    return log
```

### 6.3 Retention Policy

| Log Type | Retention | Archive | Reason |
|----------|-----------|---------|--------|
| **Security Events** (login, permission) | 7 years | Cold storage after 1 year | Compliance requirement |
| **Document Events** | 5 years | Cold storage after 1 year | Legal requirement |
| **Query Events** | 1 year | Delete after | Performance, storage cost |
| **Config Events** | 7 years | Cold storage after 1 year | Change tracking |

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        AUDIT LOG LIFECYCLE                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Hot Storage (PostgreSQL)                                                        │
│  ├── 0-12 months: All logs, full query capability                               │
│  │                                                                               │
│  │   Monthly Job: Archive old logs                                              │
│  │                                                                               │
│  Cold Storage (S3/MinIO)                                                         │
│  ├── 12-60 months: Document/Config logs (compressed JSON)                       │
│  │                                                                               │
│  │   Yearly Job: Purge expired logs                                             │
│  │                                                                               │
│  Deleted                                                                         │
│  └── > 60-84 months: Depending on log type                                      │
│                                                                                  │
│  Access:                                                                         │
│  • Hot: Direct SQL query                                                        │
│  • Cold: Restore to temp table, then query                                      │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Dependencies

### Internal Dependencies

| Component | Depends On | Purpose |
|-----------|-----------|---------|
| Permission Middleware | JWT Auth, RBAC Tables | Enforce access control |
| Searcher Service | Permission Filter Builder | Apply document-level permissions |
| Audit Logger | PostgreSQL | Store immutable logs |
| PII Scanner | Regex Engine, NER Model (optional) | Detect sensitive data |

### External Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| PostgreSQL | 15+ | RBAC tables, Audit logs |
| Redis | 7.x | Session management, rate limiting |
| Optional: Presidio | Latest | Enhanced PII detection |

### Cross-Document References

| Reference | Document | Section |
|-----------|----------|---------|
| Permission filter in Searcher | [DD-02-processing-components.md] | Searcher Service |
| Auth implementation | [DD-03-platform-services.md] | Authentication Implementation |
| Audit log schema | [DD-04-data-architecture.md] | PostgreSQL Schema |
| RBAC tables | [DD-04-data-architecture.md] | PostgreSQL Schema |

---

*Document Version: 1.0*
*Last Updated: 2026-02-02*
