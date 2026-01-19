# RAG Service - Architecture & Design Guide

> **Purpose**: Hướng dẫn kiến trúc và thiết kế hệ thống RAG Service  
> **Audience**: AI Code Generators, Developers, Architects  
> **Focus**: Theory, Concepts, Design Patterns - Không có code  
> **Version**: 3.0

---

## 1. EXECUTIVE SUMMARY

### 1.1 System Purpose

RAG Service là core component trong LLMOps Platform, cung cấp khả năng:
- **Ingestion**: Xử lý documents → chunking → embedding → indexing
- **Retrieval**: Query → search → optimize → return relevant chunks

### 1.2 Architecture Rating: ⭐⭐⭐⭐ (4/5)

| Aspect | Rating | Notes |
|--------|--------|-------|
| Modularity | 🟢 Excellent | Factory Strategy cho pluggable components |
| Scalability | 🟢 Good | Horizontal scaling với stateless services |
| Flexibility | 🟢 Excellent | Config-driven pipelines |
| Complexity | 🟡 Medium | Nhiều moving parts cần orchestration |
| Maintainability | 🟢 Good | Clear separation of concerns |

### 1.3 Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Tách Document Service riêng | Single Responsibility, dễ scale độc lập |
| Factory Strategy Pattern | Pluggable components, dễ extend |
| Config-as-Pipeline | Flexible, version-controlled, reproducible |
| Hybrid Search mặc định | Balance giữa semantic understanding và exact match |

---

## 2. SYSTEM ARCHITECTURE OVERVIEW

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              RAG SERVICE                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         API GATEWAY                                      │   │
│  │         REST APIs for Documents, KBs, Queries, Pipelines                 │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                    │                                            │
│           ┌────────────────────────┴────────────────────────┐                  │
│           │                                                 │                  │
│           ▼                                                 ▼                  │
│  ┌─────────────────────┐                      ┌─────────────────────────────┐  │
│  │                     │                      │                             │  │
│  │  DOCUMENT SERVICE   │                      │     PIPELINE SERVICE        │  │
│  │                     │                      │                             │  │
│  │  ┌───────────────┐  │                      │  ┌───────────────────────┐  │  │
│  │  │ SSOT Sync     │  │                      │  │ Pipeline Orchestrator │  │  │
│  │  │ Upload Handler│  │                      │  │                       │  │  │
│  │  │ Version Ctrl  │  │                      │  │ ┌─────────────────┐   │  │  │
│  │  │ Access Ctrl   │  │                      │  │ │ Component       │   │  │  │
│  │  └───────────────┘  │                      │  │ │ Factories       │   │  │  │
│  │                     │                      │  │ └─────────────────┘   │  │  │
│  └─────────────────────┘                      │  │                       │  │  │
│           │                                   │  │ ┌─────┐ ┌─────┐      │  │  │
│           │                                   │  │ │Parse│ │Chunk│ ...  │  │  │
│           │                                   │  │ └─────┘ └─────┘      │  │  │
│           │                                   │  └───────────────────────┘  │  │
│           │                                   │                             │  │
│           │                                   └─────────────────────────────┘  │
│           │                                                 │                  │
│  ┌────────┴─────────────────────────────────────────────────┴───────────────┐  │
│  │                           DATA LAYER                                      │  │
│  │                                                                           │  │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐             │  │
│  │  │ MinIO  │  │Postgres│  │ Milvus │  │Elastic │  │ Redis  │             │  │
│  │  │ (SSOT) │  │(Meta)  │  │(Vector)│  │(Search)│  │(Cache) │             │  │
│  │  └────────┘  └────────┘  └────────┘  └────────┘  └────────┘             │  │
│  │                                                                           │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Service Separation Rationale

| Service | Responsibility | Why Separate? |
|---------|---------------|---------------|
| **Document Service** | Quản lý lifecycle của documents | Scale independently, different access patterns |
| **Pipeline Service** | Orchestrate processing pipelines | Compute-intensive, needs different resources |

### 2.3 Communication Patterns

| Pattern | Use Case | Protocol |
|---------|----------|----------|
| Sync Request/Response | API calls, queries | REST/gRPC |
| Async Job Queue | Long-running ingestion | Message Queue |
| Event-Driven | Document updates → re-index | Event Bus |

---

## 3. DOCUMENT SERVICE ARCHITECTURE

### 3.1 Responsibilities

```
┌─────────────────────────────────────────────────────────────────┐
│                      DOCUMENT SERVICE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 Core Responsibilities                    │   │
│  │                                                         │   │
│  │  1. SSOT Synchronization                                │   │
│  │     • Connect to external sources (S3, GCS, SharePoint) │   │
│  │     • Detect changes (new, modified, deleted)           │   │
│  │     • Pull and store locally                            │   │
│  │                                                         │   │
│  │  2. User Upload Management                              │   │
│  │     • Validate file type, size, content                 │   │
│  │     • Manage storage quota per tenant                   │   │
│  │     • Store in tenant-isolated buckets                  │   │
│  │                                                         │   │
│  │  3. Version Control                                     │   │
│  │     • Immutable versioning (never overwrite)            │   │
│  │     • Track version history                             │   │
│  │     • Support rollback                                  │   │
│  │                                                         │   │
│  │  4. Access Control                                      │   │
│  │     • Document-level permissions                        │   │
│  │     • User/Team/Role-based access                       │   │
│  │     • Pre-filter for retrieval                          │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 SSOT Synchronization Design

#### 3.2.1 Concept

**SSOT (Single Source of Truth)**: Một nguồn dữ liệu tập trung chứa tất cả documents. Document Service đồng bộ từ SSOT thay vì user upload trực tiếp.

#### 3.2.2 Sync Strategy

| Strategy | Description | When to Use |
|----------|-------------|-------------|
| **Full Sync** | Scan toàn bộ source, compare với local | Initial sync, trigger theo schedule |
| **Incremental Sync** | Chỉ lấy changes từ last sync | Regular scheduled sync |
| **Event-Driven** | React to change events từ source | Real-time sync (nếu source hỗ trợ) |

#### 3.2.3 Change Detection

```
┌─────────────────────────────────────────────────────────────────┐
│                    CHANGE DETECTION FLOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  For each file in SSOT:                                         │
│                                                                 │
│  1. Compute file hash (SHA-256)                                 │
│                                                                 │
│  2. Compare with stored hash:                                   │
│     ┌─────────────────────────────────────────────────┐        │
│     │ File not in local DB     → NEW      → Download  │        │
│     │ Hash different           → MODIFIED → Download  │        │
│     │ Hash same                → UNCHANGED→ Skip      │        │
│     └─────────────────────────────────────────────────┘        │
│                                                                 │
│  3. Files in local but not in SSOT → DELETED → Mark deleted    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.2.4 Supported SSOT Sources

| Source Type | Connector | Change Detection |
|-------------|-----------|------------------|
| Amazon S3 | S3 API | LastModified + ETag |
| Google Cloud Storage | GCS API | generation number |
| Azure Blob Storage | Azure SDK | ETag |
| SharePoint/OneDrive | Graph API | delta query |
| Local Filesystem | inotify/fswatch | File watcher |
| HTTP/HTTPS | HEAD requests | ETag, Last-Modified |

### 3.3 Version Control Design

#### 3.3.1 Versioning Strategy

**Immutable Versioning**: Mỗi update tạo version mới, không bao giờ overwrite.

```
Document Lifecycle:
─────────────────────────────────────────────────────────────────

  v1 (create)      v2 (update)       v3 (update)      v4 (rollback to v2)
  ───────────      ───────────       ───────────      ────────────────────
  │               │                 │                │
  │ is_latest=T   │ is_latest=T     │ is_latest=T    │ is_latest=T
  │               │                 │                │
  └──▶ v1         └──▶ v2           └──▶ v3          └──▶ v4 (copy of v2)
       is_latest=F     is_latest=F       is_latest=F

Storage: /tenant-{id}/doc-{id}/v1/file.pdf
         /tenant-{id}/doc-{id}/v2/file.pdf
         ...
```

#### 3.3.2 Version Metadata

| Field | Description |
|-------|-------------|
| version_number | Sequential version (1, 2, 3...) |
| is_latest | Boolean flag for current version |
| parent_version | Previous version ID |
| created_by | User who created this version |
| created_at | Timestamp |
| change_note | Optional description of changes |
| file_hash | SHA-256 for integrity |

### 3.4 Access Control Design

#### 3.4.1 Permission Model

```
┌─────────────────────────────────────────────────────────────────┐
│                    ACCESS CONTROL MODEL                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Access Levels (mutually exclusive):                            │
│  ──────────────────────────────────                             │
│  │ PRIVATE      │ Only owner can access                        │
│  │ TEAM         │ Team members can access                      │
│  │ ORGANIZATION │ All org members can access                   │                │
│                                                                 │
│  Permission Types:                                              │
│  ────────────────                                               │
│  │ READ   │ View and retrieve document                         │
│  │ WRITE  │ Update, create new version                         │
│  │ DELETE │ Soft/hard delete                                   │
│  │ SHARE  │ Modify access permissions                          │
│  │ ADMIN  │ All permissions + manage document                  │
│                                                                 │
│  Grant Targets:                                                 │
│  ─────────────                                                  │
│  │ User   │ Specific user ID                                   │
│  │ Team   │ Team ID (all members inherit)                      │
│  │ Role   │ Role name (e.g., "admin", "editor")               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.4.2 Access Check Flow (for Retrieval)

```
Query Request
     │
     ▼
┌─────────────────────────────────────┐
│  1. Extract user context            │
│     (user_id, teams, roles)         │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│  2. Get accessible document IDs     │
│     - Documents user owns           │
│     - Documents shared to user      │
│     - Documents shared to teams     │
│     - Documents shared by role      │
│     - Organization documents        │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│  3. Pass document IDs to Searcher   │
│     as pre-filter                   │
│     (filter BEFORE search, not      │
│      filter results AFTER)          │
└─────────────────────────────────────┘
     │
     ▼
Search Results (only accessible docs)
```

**🔴 Critical**: Access filtering phải xảy ra TRƯỚC search (pre-filter), không phải sau. Post-filter có thể leak document existence.

---

## 4. PIPELINE SERVICE ARCHITECTURE

### 4.1 Design Pattern: Factory Strategy

#### 4.1.1 Pattern Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    FACTORY STRATEGY PATTERN                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Problem: Cần hỗ trợ nhiều implementations cho cùng một task    │
│           (ví dụ: nhiều chunking strategies)                    │
│                                                                 │
│  Solution:                                                      │
│  ─────────                                                      │
│                                                                 │
│  ┌─────────────────┐     ┌─────────────────┐                   │
│  │  User Config    │     │    Factory      │                   │
│  │  (YAML/JSON)    │────▶│                 │                   │
│  │                 │     │  .create(type)  │                   │
│  │  type: "semantic"     │                 │                   │
│  │  config: {...}  │     └────────┬────────┘                   │
│  └─────────────────┘              │                             │
│                                   │ lookup registry             │
│                                   ▼                             │
│                          ┌───────────────┐                      │
│                          │   Registry    │                      │
│                          │ ┌───────────┐ │                      │
│                          │ │"semantic" │─┼──▶ SemanticChunker   │
│                          │ │"recursive"│─┼──▶ RecursiveChunker  │
│                          │ │"fixed"    │─┼──▶ FixedChunker      │
│                          │ └───────────┘ │                      │
│                          └───────────────┘                      │
│                                   │                             │
│                                   ▼                             │
│                          ┌───────────────┐                      │
│                          │   Instance    │                      │
│                          │  with config  │                      │
│                          │   applied     │                      │
│                          └───────────────┘                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 4.1.2 Why Factory Strategy?

| Alternative | Pros | Cons | Decision |
|-------------|------|------|----------|
| **If-else chain** | Simple | Hard to extend, violates OCP | ❌ |
| **Plugin system** | Very flexible | Runtime errors, version conflicts | ❌ |
| **Factory Strategy** | Type-safe, extensible, testable | Slightly more code | ✅ |

#### 4.1.3 Adding New Component (Theory) -> demo for future plan

```
To add new Chunker "my_custom":

1. Create class implementing BaseChunker interface
   - Define component_type() → "my_custom"
   - Define config_schema() → JSON Schema for validation
   - Implement chunk() method

2. Register with Factory (decorator or explicit)
   - Factory maintains registry: {"my_custom": MyCustomChunker}

3. Component now available:
   - In API: GET /components/chunkers lists it
   - In config: chunker.type: "my_custom"
   - Factory.create("my_custom", config) returns instance
```

### 4.2 Component Categories

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         PIPELINE COMPONENT TAXONOMY                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                        INGESTION PIPELINE                                │   │
│  │                                                                         │   │
│  │  Document ──▶ [PARSER] ──▶ [CHUNKER] ──▶ [EMBEDDER] ──▶ [INDEXER]      │   │
│  │                                                                         │   │
│  │  Each slot has a Factory with multiple implementations                  │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                        RETRIEVAL PIPELINE                                │   │
│  │                                                                         │   │
│  │  Query ──▶ [SEARCHER] ──▶ [OPTIMIZER CHAIN] ──▶ Results                │   │
│  │             (Pick ONE)    (Pick 0 or MORE)                              │   │
│  │                                                                         │   │
│  │  Searcher: Core search algorithm                                        │   │
│  │  Optimizer: Post-processing to improve results                          │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Ingestion Pipeline Components

#### 4.3.1 Parser Factory

**Purpose**: Extract text content from various document formats.

| Component | Input | Output | Best For |
|-----------|-------|--------|----------|
| **pdf** | PDF bytes | Text + metadata + tables | Standard PDFs |
| **pdf_ocr** | Scanned PDF bytes | OCR-extracted text | Scanned documents |
| **docx** | DOCX bytes | Text + structure | Word documents |
| **html** | HTML string | Clean text | Web pages |
| **markdown** | MD string | Text + structure | Documentation |
| **csv** | CSV bytes | Structured text | Tabular data |
| **excel** | XLSX bytes | Text per sheet | Spreadsheets |

**Parser Selection Logic**:
```
1. Check file extension
2. Verify with magic bytes (actual file type)
3. Route to appropriate parser
4. Fallback: plain text extraction
```

#### 4.3.2 Chunker Factory

**Purpose**: Split text into smaller, semantically meaningful chunks.

| Component | Strategy | Config | Best For |
|-----------|----------|--------|----------|
| **recursive** | Try separators hierarchically (¶ → \n → . → space) | chunk_size, overlap, separators | General text |
| **semantic** | Use embeddings to detect topic boundaries | similarity_threshold, min/max_size | Mixed-topic docs |
| **fixed** | Fixed character/token count | chunk_size, overlap | Uniform processing |
| **sentence** | Split by sentences, group to size | sentences_per_chunk | Structured text |
| **markdown** | Respect markdown structure (headers, code blocks) | heading_level | Documentation |
| **code** | Respect code structure (functions, classes) | language, granularity | Source code |

**Chunking Decision Matrix**:

| Document Type | Recommended Chunker | Reasoning |
|---------------|---------------------|-----------|
| General articles | recursive | Works well for most text |
| Long reports with sections | semantic | Respects topic changes |
| Technical documentation | markdown | Preserves structure |
| Code repositories | code | Maintains code semantics |
| Legal documents | sentence | Sentence integrity important |

#### 4.3.3 Embedder Factory -> cost free will be optimized

**Purpose**: Convert text chunks to dense vector representations.

| Component | Provider | Dimensions | Speed | Quality | Cost |
|-----------|----------|------------|-------|---------|------|
| **openai_small** | OpenAI | 1536 | Fast | Good | $ |
| **openai_large** | OpenAI | 3072 | Medium | Excellent | $$ |
| **local_minilm** | Local | 384 | Very Fast | Moderate | Free |
| **local_e5** | Local | 768 | Fast | Good | Free |
| **cohere** | Cohere | 1024 | Fast | Good | $ |
| **voyage** | Voyage AI | 1024 | Fast | Excellent | $$ |

**Embedder Selection Criteria**:

| Priority | Recommendation |
|----------|----------------|
| Quality first, cloud OK | OpenAI large |
| Balance quality/cost | OpenAI small |
| On-premise required | Local E5 or similar |
| Multi-language | Cohere multilingual |

**🔴 Critical**: Ingestion và Retrieval PHẢI dùng cùng embedder model. Khác model = không thể search.

#### 4.3.4 Indexer Factory

**Purpose**: Store chunks and embeddings for efficient retrieval.

| Component | Storage | Search Type | Best For |
|-----------|---------|-------------|----------|
| **milvus** | Milvus | Vector only | Semantic search |
| **elasticsearch** | Elasticsearch | Full-text only | Keyword search |
| **hybrid** | Milvus + ES | Both | Combined search |

**Index Type Selection (Milvus)**:

| Index | Speed | Accuracy | Memory | Best For |
|-------|-------|----------|--------|----------|
| FLAT | Slow | 100% | High | Small datasets (<100K) |
| IVF_FLAT | Fast | ~95% | Medium | Medium datasets |
| IVF_SQ8 | Faster | ~90% | Low | Large datasets, memory constrained |
| HNSW | Very Fast | ~98% | High | Production, high recall needed |

### 4.4 Retrieval Pipeline Components

#### 4.4.1 Searcher Factory

**Purpose**: Execute the core search algorithm.

**🔴 Rule**: Pick exactly ONE searcher. Cannot combine at this level.

| Component | Algorithm | Needs Embedding | Best For |
|-----------|-----------|-----------------|----------|
| **semantic** | Vector similarity (cosine/L2) | ✅ Yes | Conceptual similarity |
| **fulltext** | BM25 / TF-IDF | ❌ No | Exact keyword match |
| **hybrid** | Semantic + Fulltext + RRF fusion | ✅ Yes | General purpose |

**Hybrid Search: Reciprocal Rank Fusion (RRF)**

```
┌─────────────────────────────────────────────────────────────────┐
│                    HYBRID SEARCH WITH RRF                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Query: "how to reset password"                                 │
│                                                                 │
│  ┌─────────────────────┐    ┌─────────────────────┐            │
│  │   Semantic Search   │    │   Fulltext Search   │            │
│  │   (Milvus)          │    │   (Elasticsearch)   │            │
│  └──────────┬──────────┘    └──────────┬──────────┘            │
│             │                          │                        │
│             ▼                          ▼                        │
│  Rank 1: Doc A (0.92)       Rank 1: Doc B (12.5)               │
│  Rank 2: Doc C (0.85)       Rank 2: Doc A (10.2)               │
│  Rank 3: Doc B (0.78)       Rank 3: Doc D (8.1)                │
│                                                                 │
│  ─────────────────────────────────────────────────────         │
│                                                                 │
│  RRF Formula: score(d) = Σ weight_i / (k + rank_i)             │
│                                                                 │
│  With k=60, semantic_weight=0.7:                               │
│                                                                 │
│  Doc A: 0.7/(60+1) + 0.3/(60+2) = 0.0115 + 0.0048 = 0.0163    │
│  Doc B: 0.7/(60+3) + 0.3/(60+1) = 0.0111 + 0.0049 = 0.0160    │
│  Doc C: 0.7/(60+2) + 0.0       = 0.0113                        │
│  Doc D: 0.0       + 0.3/(60+3) = 0.0048                        │
│                                                                 │
│  Final Ranking: A > B > C > D                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Why RRF?**
- Score normalization: Không cần normalize scores từ khác sources
- Rank-based: Chỉ cần relative ordering, không cần absolute scores
- Tunable: semantic_weight điều chỉnh balance

#### 4.4.2 Optimizer Factory

**Purpose**: Post-process search results to improve quality.

**🟢 Rule**: Pick ZERO or MORE optimizers. They chain in order.

| Component | Order | Function | Input | Output |
|-----------|-------|----------|-------|--------|
| **reranking** | 10 | Re-score with cross-encoder | N results | N results (reordered) |
| **score_threshold** | 20 | Filter by minimum score | N results | ≤N results |
| **metadata_filter** | 25 | Filter by metadata conditions | N results | ≤N results |
| **deduplication** | 30 | Remove similar chunks | N results | ≤N results |
| **diversity** | 35 | Ensure diverse results (MMR) | N results | ≤N results |
| **max_results** | 100 | Limit count | N results | top_k results |

**Optimizer Chain Example**:

```
Search Results (20 items)
         │
         ▼
┌────────────────────┐
│ Reranking (10)     │  Cross-encoder re-scores all 20
└────────┬───────────┘
         │ (20 items, reordered)
         ▼
┌────────────────────┐
│ Score Threshold    │  Remove items with score < 0.5
│ (20)               │
└────────┬───────────┘
         │ (15 items)
         ▼
┌────────────────────┐
│ Deduplication (30) │  Remove near-duplicates
└────────┬───────────┘
         │ (12 items)
         ▼
┌────────────────────┐
│ Max Results (100)  │  Return top 5
└────────┬───────────┘
         │
         ▼
Final Results (5 items)
```

**Reranking Deep Dive**:

| Aspect | Bi-Encoder (Search) | Cross-Encoder (Rerank) |
|--------|---------------------|------------------------|
| Speed | Fast (pre-computed embeddings) | Slow (compute at query time) |
| Accuracy | Good | Better |
| Use case | Initial retrieval | Re-score top candidates |
| Scale | Millions of docs | Top 10-50 candidates |

**Why Reranking Helps**:
- Bi-encoder embeds query và document independently → có thể miss fine-grained matching
- Cross-encoder processes query+document together → better understanding

---

## 5. DATA MODEL DESIGN

### 5.1 Entity Relationship

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           ENTITY RELATIONSHIPS                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────┐                                                                   │
│  │  Tenant  │                                                                   │
│  └────┬─────┘                                                                   │
│       │ 1:N                                                                     │
│       ▼                                                                         │
│  ┌──────────┐       N:M        ┌────────────────┐                              │
│  │ Document │◄────────────────▶│ Knowledge Base │                              │
│  └────┬─────┘                  └───────┬────────┘                              │
│       │ 1:N                            │ 1:N                                    │
│       ▼                                ▼                                        │
│  ┌──────────┐                   ┌──────────┐                                   │
│  │ Version  │                   │  Chunk   │                                   │
│  └──────────┘                   └──────────┘                                   │
│                                                                                 │
│  ┌──────────┐                   ┌──────────────┐                               │
│  │ Document │ 1:N               │ Pipeline Run │                               │
│  │Permission│◄──────────────────│              │                               │
│  └──────────┘                   └──────────────┘                               │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Core Entities

#### 5.2.1 Document

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| tenant_id | UUID | FK to Tenant |
| filename | String | Original filename |
| file_type | Enum | pdf, docx, txt, etc. |
| file_size_bytes | Long | File size |
| file_hash | String | SHA-256 for dedup |
| storage_path | String | Path in MinIO |
| source_type | Enum | ssot, user_upload |
| version | Integer | Version number |
| is_latest | Boolean | Latest version flag |
| status | Enum | pending, processing, completed, failed |
| created_at | Timestamp | Creation time |

#### 5.2.2 Knowledge Base

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| tenant_id | UUID | FK to Tenant |
| name | String | KB name |
| description | String | Description |
| kb_type | Enum | semantic, fulltext, hybrid |
| ingestion_config | JSONB | Full ingestion pipeline config |
| retrieval_config | JSONB | Default retrieval pipeline config |
| total_documents | Integer | Count of documents |
| total_chunks | Integer | Count of chunks |
| status | Enum | creating, ready, updating, failed |

#### 5.2.3 Chunk

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| kb_id | UUID | FK to Knowledge Base |
| document_id | UUID | FK to Document |
| content | Text | Chunk text content |
| content_hash | String | For deduplication |
| chunk_index | Integer | Position in document |
| start_char | Integer | Start position |
| end_char | Integer | End position |
| metadata | JSONB | Custom metadata |
| milvus_id | String | ID in Milvus |
| elasticsearch_id | String | ID in ES |

### 5.3 Storage Strategy

| Data Type | Storage | Reasoning |
|-----------|---------|-----------|
| Documents (files) | MinIO | Object storage, S3-compatible |
| Metadata | PostgreSQL | ACID, complex queries |
| Vectors | Milvus | Optimized for ANN search |
| Full-text index | Elasticsearch | Optimized for BM25 |
| Cache | Redis | Fast, ephemeral |
| Embeddings cache | PostgreSQL/Redis | Avoid recomputation |

---

## 6. PIPELINE CONFIGURATION DESIGN

### 6.1 Configuration Philosophy

```
┌─────────────────────────────────────────────────────────────────┐
│                 CONFIGURATION AS CODE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Principles:                                                    │
│  ───────────                                                    │
│  1. Declarative: Describe WHAT, not HOW                        │
│  2. Versionable: Store in Git, track changes                   │
│  3. Validatable: JSON Schema for each component                │
│  4. Reproducible: Same config → same results                   │
│  5. Composable: Mix and match components                       │
│                                                                 │
│  Benefits:                                                      │
│  ─────────                                                      │
│  • Easy experimentation (change config, not code)              │
│  • A/B testing pipelines                                        │
│  • Audit trail of configuration changes                        │
│  • Share configs between teams                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Ingestion Pipeline Config Structure

```yaml
# ingestion_config.yaml

name: "Advanced Ingestion Pipeline"
version: "1.0"

ingestion:
  # ──────────────────────────────────────────────────────
  # PARSER SLOT
  # Responsible for: Extract text from documents
  # ──────────────────────────────────────────────────────
  parser:
    type: "auto"              # auto-detect by file type
    config:
      ocr_enabled: true       # Enable OCR for scanned docs
      ocr_language: "eng"     # Tesseract language
      extract_tables: true    # Extract tables as text
      extract_images: false   # Extract embedded images

  # ──────────────────────────────────────────────────────
  # CHUNKER SLOT
  # Responsible for: Split text into chunks
  # ──────────────────────────────────────────────────────
  chunker:
    type: "recursive"         # recursive | semantic | fixed | ...
    config:
      chunk_size: 512         # Target chunk size (chars)
      chunk_overlap: 50       # Overlap between chunks
      separators:             # Try in order
        - "\n\n"
        - "\n"
        - ". "
        - " "

  # ──────────────────────────────────────────────────────
  # EMBEDDER SLOT
  # Responsible for: Convert chunks to vectors
  # ──────────────────────────────────────────────────────
  embedder:
    type: "openai"            # openai | local | cohere | ...
    config:
      model: "text-embedding-3-small"
      batch_size: 32

  # ──────────────────────────────────────────────────────
  # INDEXER SLOT
  # Responsible for: Store chunks + vectors
  # ──────────────────────────────────────────────────────
  indexer:
    type: "hybrid"            # milvus | elasticsearch | hybrid
    config:
      milvus:
        index_type: "IVF_FLAT"
        metric_type: "COSINE"
        nlist: 1024
      elasticsearch:
        analyzer: "standard"
```

### 6.3 Retrieval Pipeline Config Structure

```yaml
# retrieval_config.yaml

name: "Hybrid Search with Reranking"
version: "1.0"

retrieval:
  # ──────────────────────────────────────────────────────
  # EMBEDDER (for query)
  # Must match ingestion embedder!
  # ──────────────────────────────────────────────────────
  embedder:
    type: "openai"
    config:
      model: "text-embedding-3-small"   # MUST match ingestion

  # ──────────────────────────────────────────────────────
  # SEARCHER SLOT (Required, pick ONE)
  # Responsible for: Core search algorithm
  # ──────────────────────────────────────────────────────
  searcher:
    type: "hybrid"            # semantic | fulltext | hybrid
    config:
      semantic_weight: 0.7    # 0.7 semantic + 0.3 fulltext
      rrf_k: 60               # RRF smoothing constant
      fetch_multiplier: 2.0   # Fetch 2x for optimization stage

  # ──────────────────────────────────────────────────────
  # OPTIMIZER SLOTS (Optional, pick 0 or more)
  # Responsible for: Post-process results
  # Executed in order by 'order' property
  # ──────────────────────────────────────────────────────
  optimizers:
    - type: "reranking"
      config:
        model: "cross-encoder/ms-marco-MiniLM-L-6-v2"
        top_k: 10             # Rerank top 10

    - type: "score_threshold"
      config:
        min_score: 0.3        # Filter below 0.3

    - type: "deduplication"
      config:
        similarity_threshold: 0.9
        method: "jaccard"

    - type: "max_results"
      config:
        max_results: 5        # Return top 5
```

### 6.4 Component Selection Guide

#### For Chunking:

```
┌─────────────────────────────────────────────────────────────────┐
│                    CHUNKER SELECTION GUIDE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Document Type           │ Recommended Chunker                  │
│  ────────────────────────┼────────────────────────────────────  │
│  General articles        │ recursive (default)                  │
│  Mixed-topic reports     │ semantic                             │
│  Technical docs          │ markdown                             │
│  Source code             │ code                                 │
│  Legal/contracts         │ sentence                             │
│  Structured data         │ fixed                                │
│                                                                 │
│  Key Parameters:                                                │
│  ───────────────                                                │
│  chunk_size: 256-1024 (smaller = more precise, larger = more   │
│              context)                                           │
│  overlap: 10-20% of chunk_size (prevents cutting sentences)    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### For Search:

```
┌─────────────────────────────────────────────────────────────────┐
│                    SEARCHER SELECTION GUIDE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Query Type              │ Recommended Searcher                 │
│  ────────────────────────┼────────────────────────────────────  │
│  Conceptual questions    │ semantic                             │
│  Exact keyword lookup    │ fulltext                             │
│  General purpose         │ hybrid (recommended)                 │
│                                                                 │
│  Hybrid Config Tips:                                            │
│  ───────────────────                                            │
│  semantic_weight: 0.7    │ Default, balanced                    │
│  semantic_weight: 0.9    │ Concept-heavy queries                │
│  semantic_weight: 0.5    │ Keyword-heavy queries                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### For Optimization:

```
┌─────────────────────────────────────────────────────────────────┐
│                   OPTIMIZER SELECTION GUIDE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Need                    │ Optimizer                            │
│  ────────────────────────┼────────────────────────────────────  │
│  Higher accuracy         │ reranking (cross-encoder)            │
│  Remove low quality      │ score_threshold                      │
│  Remove duplicates       │ deduplication                        │
│  Diverse results         │ diversity (MMR)                      │
│  Limit count             │ max_results                          │
│                                                                 │
│  Recommended Chain:                                             │
│  ─────────────────                                              │
│  reranking → score_threshold → deduplication → max_results     │
│                                                                 │
│  Latency Considerations:                                        │
│  ───────────────────────                                        │
│  • reranking: +50-200ms (model inference)                      │
│  • score_threshold: +1ms (filter)                              │
│  • deduplication: +5-20ms (similarity computation)             │
│  • max_results: +0ms (slice)                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. QUALITY METRICS & EVALUATION

### 7.1 Retrieval Quality Metrics

| Metric | Formula | Meaning |
|--------|---------|---------|
| **Precision@K** | relevant_in_top_k / k | % relevant trong top K |
| **Recall@K** | relevant_in_top_k / total_relevant | % relevant found trong top K |
| **MRR** | 1/rank_of_first_relevant | Vị trí của first relevant |
| **NDCG@K** | DCG@K / IDCG@K | Ranking quality |
| **Hit Rate** | queries_with_hit / total_queries | % queries có ít nhất 1 relevant |

### 7.2 Latency Targets

| Component | P50 Target | P95 Target | P99 Target |
|-----------|------------|------------|------------|
| Query Embedding | 50ms | 100ms | 150ms |
| Vector Search | 30ms | 80ms | 120ms |
| Fulltext Search | 20ms | 50ms | 80ms |
| Reranking (top 10) | 100ms | 200ms | 300ms |
| **Total Retrieval** | **200ms** | **400ms** | **600ms** |

### 7.3 RAG Triad Evaluation

```
┌─────────────────────────────────────────────────────────────────┐
│                        RAG TRIAD                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                        ┌─────────┐                              │
│                        │  QUERY  │                              │
│                        └────┬────┘                              │
│                             │                                   │
│              ┌──────────────┼──────────────┐                   │
│              │              │              │                   │
│              ▼              │              ▼                   │
│       ┌──────────┐          │       ┌──────────┐              │
│       │ CONTEXT  │◄─────────┴──────▶│ RESPONSE │              │
│       │(Retrieved)│                 │(Generated)│              │
│       └─────┬────┘                  └─────┬────┘              │
│             │                             │                    │
│             └──────────────┬──────────────┘                    │
│                            │                                   │
│                      FAITHFULNESS                              │
│                                                                 │
│  Metrics:                                                       │
│  ─────────                                                      │
│  Query ↔ Context:  Context Relevancy (retrieved relevant?)     │
│  Query ↔ Response: Answer Relevancy (answer on-topic?)         │
│  Context ↔ Response: Faithfulness (answer grounded in context?)│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. SCALABILITY & PERFORMANCE

### 8.1 Scaling Strategy

| Component | Scaling Type | Strategy |
|-----------|--------------|----------|
| API Gateway | Horizontal | Load balancer + multiple instances |
| Document Service | Horizontal | Stateless, scale by traffic |
| Pipeline Service | Horizontal | Scale by job queue depth |
| Milvus | Horizontal | Sharding by KB |
| Elasticsearch | Horizontal | Index sharding |
| PostgreSQL | Vertical + Read replicas | Write to primary, read from replicas |
| MinIO | Horizontal | Distributed mode |

### 8.2 Bottleneck Analysis

```
┌─────────────────────────────────────────────────────────────────┐
│                    LATENCY BREAKDOWN                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Retrieval Pipeline (P95):                                      │
│  ──────────────────────────                                     │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Query Processing          ████                    50ms  │   │
│  │ Embedding                 ████████                100ms │   │
│  │ Vector Search             ██████                   80ms │   │
│  │ Fulltext Search           ████                     50ms │   │
│  │ RRF Fusion                █                        10ms │   │
│  │ Reranking                 ████████████████        200ms │   │ 🔴 Bottleneck
│  │ Post-processing           ██                       20ms │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Total: ~510ms                                                  │
│                                                                 │
│  Optimization Opportunities:                                    │
│  ────────────────────────────                                   │
│  1. Reranking: Use smaller model or GPU                        │
│  2. Embedding: Cache frequent queries                          │
│  3. Parallel: Run vector + fulltext search in parallel         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.3 Caching Strategy

| Cache Layer | What to Cache | TTL | Hit Rate Target |
|-------------|---------------|-----|-----------------|
| Query Embedding | Hash(query) → embedding | 1 hour | 30-40% |
| Chunk Content | chunk_id → content | 24 hours | 80%+ |
| Search Results | Hash(query+kb_id) → results | 5 min | 20-30% |

---

## 9. SECURITY CONSIDERATIONS

### 9.1 Security Layers

| Layer | Threats | Mitigations |
|-------|---------|-------------|
| **Network** | Interception, MITM | TLS everywhere, VPC |
| **API** | Unauthorized access | JWT auth, rate limiting |
| **Data** | Data breach | Encryption at rest, field-level encryption |
| **AI-Specific** | Prompt injection | Input validation, guardrails |
| **Document** | Unauthorized access | Document-level ACL |

### 9.2 AI-Specific Security

| Risk | Description | Mitigation |
|------|-------------|------------|
| **Prompt Injection** | Malicious instructions in documents | Input sanitization, guardrails |
| **Data Poisoning** | Bad data affects retrieval | Content validation, source verification |
| **Information Leakage** | Sensitive data in responses | PII detection, access control |
| **Model Extraction** | Stealing embeddings | Rate limiting, watermarking |

---

## 10. ARCHITECTURE SCORECARD

| Dimension | Score | Notes |
|-----------|-------|-------|
| **Modularity** | 9/10 | Factory pattern, clean separation |
| **Scalability** | 8/10 | Horizontal scaling, some bottlenecks |
| **Flexibility** | 9/10 | Config-driven, pluggable components |
| **Security** | 7/10 | Good ACL, needs AI-specific hardening |
| **Observability** | 6/10 | Needs more ML-specific monitoring |
| **Cost Efficiency** | 7/10 | Caching helps, embedding costs high |
| **Reliability** | 7/10 | Needs retry logic, circuit breakers |
| **Performance** | 7/10 | Reranking bottleneck |
| **Maintainability** | 8/10 | Clear patterns, good separation |
| **Compliance** | 6/10 | Needs audit logging, GDPR features |

**Overall: 7.4/10** 🟢

---

## 11. IMPLEMENTATION ROADMAP

### Phase 1: Foundation (Week 1-2)
- [ ] Document Service với SSOT sync
- [ ] Basic PostgreSQL schema
- [ ] MinIO setup và storage service

### Phase 2: Core Pipeline (Week 3-4)
- [ ] Parser Factory với PDF, DOCX, TXT
- [ ] Chunker Factory với recursive, fixed
- [ ] Embedder Factory với OpenAI, local
- [ ] Indexer Factory với Milvus

### Phase 3: Retrieval (Week 5-6)
- [ ] Searcher Factory với semantic, fulltext, hybrid
- [ ] Optimizer Factory với reranking, threshold, dedup
- [ ] Pipeline orchestrator

### Phase 4: Production Ready (Week 7-8)
- [ ] API layer với authentication
- [ ] Caching layer
- [ ] Monitoring và logging
- [ ] Documentation

---

## Limitation
- Cache layer: model cache, query cache
- Data lineage tracking
- fallback strategies
- rate limit
- retry
- observation tools
- model drift
- A/B testing

---
*Document Version: 3.0*  
*Focus: Architecture Theory & Design Concepts*  
*Last Updated: 2025-01-19*