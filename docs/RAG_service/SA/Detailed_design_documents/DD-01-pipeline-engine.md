# Detailed Design — Pipeline Engine & Orchestration

**Document ID:** DD-01
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

- [1. Purpose & Scope](#1-purpose--scope)
- [2. Pipeline Config Schema](#2-pipeline-config-schema)
  - [2.1 Ingestion Pipeline Config](#21-ingestion-pipeline-config)
  - [2.2 Retrieval Pipeline Config](#22-retrieval-pipeline-config)
  - [2.3 Config Validation Rules](#23-config-validation-rules)
- [3. Pipeline Builder](#3-pipeline-builder)
  - [3.1 Factory Pattern Design](#31-factory-pattern-design)
  - [3.2 Strategy Registration](#32-strategy-registration)
  - [3.3 Dynamic Pipeline Construction](#33-dynamic-pipeline-construction)
- [4. Pipeline Executor](#4-pipeline-executor)
  - [4.1 Execution Model](#41-execution-model)
  - [4.2 Step Orchestration](#42-step-orchestration)
  - [4.3 Error Handling & Recovery](#43-error-handling--recovery)
- [5. Ingestion Pipeline Definition](#5-ingestion-pipeline-definition)
  - [5.1 Pipeline Steps](#51-pipeline-steps)
  - [5.2 Step Dependencies & Constraints](#52-step-dependencies--constraints)
  - [5.3 Sequence Diagram](#53-sequence-diagram)
- [6. Retrieval Pipeline Definition](#6-retrieval-pipeline-definition)
  - [6.1 Pipeline Steps](#61-pipeline-steps)
  - [6.2 Optional vs Required Steps](#62-optional-vs-required-steps)
  - [6.3 Sequence Diagram](#63-sequence-diagram)
- [7. Queue Architecture](#7-queue-architecture)
  - [7.1 Queue Design](#71-queue-design)
  - [7.2 Message Schema](#72-message-schema)
  - [7.3 Worker Lifecycle](#73-worker-lifecycle)
- [8. Config Versioning & Migration](#8-config-versioning--migration)
- [9. Dependencies](#9-dependencies)

---

## 1. Purpose & Scope

### Purpose

Document này mô tả cơ chế hoạt động cốt lõi của hệ thống RAG Service QuickWin — cách một pipeline được sinh ra từ config và thực thi. Đây là tài liệu nền tảng, định nghĩa "mental model" mà mọi developer cần nắm trước khi implement bất kỳ component nào.

### Scope

Pipeline Engine chịu trách nhiệm:
- Parse và validate pipeline configuration
- Build pipeline từ config thông qua factory pattern
- Orchestrate việc thực thi sequential các steps trong pipeline
- Handle errors và recovery trong quá trình processing

### Out of Scope

- Chi tiết implementation của từng processing component (xem [DD-02-processing-components.md])
- Database schema (xem [DD-04-data-architecture.md])
- RBAC policies (xem [DD-05-data-governance.md])

---

## 2. Pipeline Config Schema

Hệ thống sử dụng **Config-as-Pipeline** pattern, cho phép user định nghĩa pipeline behavior thông qua JSON configuration. Config được lưu trong PostgreSQL và gửi kèm message vào queue.

### 2.1 Ingestion Pipeline Config

```json
{
  "pipeline_id": "ingestion_pipeline_001",
  "kb_id": "kb_001",
  "version": "1.0",
  "created_at": "2026-02-02T10:00:00Z",

  "parser": {
    "pdf": {
      "method": "pypdf",
      "lang": "Vietnamese",
      "output_format": "text"
    },
    "image": {
      "method": "vlm",
      "llm_id": "gpt-4-vision",
      "output_format": "text"
    },
    "audio": {
      "method": "whisper",
      "llm_id": "whisper-large-v3",
      "output_format": "text"
    },
    "document": {
      "method": "unstructured",
      "output_format": "text"
    },
    "spreadsheet": {
      "method": "pandas",
      "output_format": "json"
    },
    "code": {
      "method": "treesitter",
      "output_format": "ast"
    }
  },

  "chunker": {
    "text": {
      "method": "recursive_semantic",
      "chunk_size": 512,
      "chunk_overlap": 50,
      "separators": ["\n\n", "\n", ". ", " "],
      "length_function": "token_count",
      "preserve_metadata": true
    },
    "table": {
      "method": "row_group",
      "rows_per_chunk": 20,
      "include_header": true,
      "overlap_rows": 2,
      "preserve_structure": true,
      "output_format": "markdown_table"
    },
    "code": {
      "method": "ast_semantic",
      "granularity": "function",
      "max_chunk_size": 1000,
      "include_context": true,
      "preserve_imports": true
    },
    "mixed": {
      "method": "adaptive",
      "detect_boundaries": true,
      "fallback": "text"
    }
  },

  "embedding": {
    "text": {
      "model": "jinaai-v3",
      "base_url": "aiep_path",
      "dimension": 3072,
      "batch_size": 100,
      "max_tokens": 8191
    },
    "table": {
      "model": "embed-multilingual-v3.0",
      "base_url": "aiep_path",
      "dimension": 3072,
      "batch_size": 100,
      "max_tokens": 8191
    },
    "code": {
      "model": "voyage_code",
      "base_url": "aiep_path",
      "dimension": 3072,
      "batch_size": 100,
      "max_tokens": 8191
    }
  },

  "indexing": {
    "strategy": "multi_collection",
    "vector_db": {
      "type": "milvus",
      "collections": {
        "text": {
          "name": "kb_text",
          "index_type": "AUTOINDEX",
          "metric_type": "COSINE",
          "partition_key": "source_id"
        },
        "table": {
          "name": "kb_table",
          "index_type": "AUTOINDEX",
          "metric_type": "COSINE",
          "partition_key": "source_id"
        },
        "code": {
          "name": "kb_code",
          "index_type": "AUTOINDEX",
          "metric_type": "COSINE",
          "partition_key": "language"
        }
      }
    },
    "keyword_db": {
      "type": "elasticsearch",
      "indices": {
        "text": {
          "name": "kb_text_keyword",
          "analyzer": "vietnamese"
        },
        "table": {
          "name": "kb_table_keyword",
          "analyzer": "standard"
        },
        "code": {
          "name": "kb_code_keyword",
          "analyzer": "standard"
        }
      }
    }
  }
}
```

### 2.2 Retrieval Pipeline Config

**Semantic Search Configuration:**

```json
{
  "pipeline_id": "retrieval_pipeline_001",
  "kb_id": "kb_001",
  "version": "1.0",

  "prompt_processing": {
    "enabled": false,
    "methods": []
  },

  "search": {
    "type": "semantic",
    "similarity_threshold": 0.2,
    "top_k": 10
  },

  "reranking": {
    "enabled": false,
    "model": "bge-reranker-v2",
    "base_url": "aiep_path",
    "top_k": 5
  },

  "llm": {
    "model": "gpt-4",
    "base_url": "aiep_path",
    "temperature": 0.7
  }
}
```

**Hybrid Search Configuration:**

```json
{
  "pipeline_id": "retrieval_pipeline_002",
  "kb_id": "kb_001",
  "version": "1.0",

  "prompt_processing": {
    "enabled": true,
    "methods": ["query_expansion", "query_rewrite"]
  },

  "search": {
    "type": "hybrid",
    "vector_weight": 0.6,
    "keyword_weight": 0.4,
    "fusion_method": "rrf",
    "similarity_threshold": 0.2,
    "top_k": 10
  },

  "reranking": {
    "enabled": true,
    "model": "bge-reranker-v2",
    "base_url": "aiep_path",
    "top_k": 5
  },

  "llm": {
    "model": "gpt-4",
    "base_url": "aiep_path",
    "temperature": 0.7,
    "max_tokens": 2048,
    "stream": true
  }
}
```

### 2.3 Config Validation Rules

| Rule | Validation | Error Message |
|------|------------|---------------|
| **Required Fields** | `kb_id`, `embedding.model` must exist | "Missing required field: {field}" |
| **Dimension Consistency** | All embedding models must have same dimension within a KB | "Embedding dimension mismatch: expected {dim1}, got {dim2}" |
| **Search Type** | Must be one of: `semantic`, `keyword`, `hybrid` | "Invalid search type: {type}" |
| **Weight Range** | `vector_weight` + `keyword_weight` must equal 1.0 for hybrid | "Hybrid search weights must sum to 1.0" |
| **Top-K Constraint** | `reranking.top_k` <= `search.top_k` | "Reranking top_k cannot exceed search top_k" |
| **Model Existence** | Referenced models must be registered in system | "Unknown model: {model_name}" |

**Validation Flow:**

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           CONFIG VALIDATION FLOW                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Input Config                                                                    │
│       │                                                                          │
│       ▼                                                                          │
│  ┌─────────────────┐                                                            │
│  │ Schema Validate │── Check JSON structure matches Pydantic schema             │
│  └────────┬────────┘                                                            │
│           │                                                                      │
│           ▼                                                                      │
│  ┌─────────────────┐                                                            │
│  │ Field Validate  │── Check required fields, types, ranges                     │
│  └────────┬────────┘                                                            │
│           │                                                                      │
│           ▼                                                                      │
│  ┌─────────────────┐                                                            │
│  │Cross-Reference  │── Check model exists, dimension consistency                │
│  │    Validate     │                                                            │
│  └────────┬────────┘                                                            │
│           │                                                                      │
│           ▼                                                                      │
│  ┌─────────────────┐                                                            │
│  │ Conflict Detect │── Check incompatible combinations                          │
│  └────────┬────────┘                                                            │
│           │                                                                      │
│       ┌───┴───┐                                                                  │
│       │       │                                                                  │
│     PASS    FAIL                                                                 │
│       │       │                                                                  │
│       ▼       ▼                                                                  │
│   Continue  Return ValidationError                                              │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Pipeline Builder

### 3.1 Factory Pattern Design

Pipeline Builder sử dụng Factory Pattern để tạo concrete implementations từ config. Mỗi processing component được đăng ký vào một factory dictionary.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           FACTORY PATTERN DESIGN                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                          COMPONENT FACTORIES                              │   │
│  │                                                                           │   │
│  │  PARSER_FACTORY = {                                                       │   │
│  │      "pypdf": PyPDFParser,                                               │   │
│  │      "vlm": VLMParser,                                                   │   │
│  │      "whisper": WhisperParser,                                           │   │
│  │      "unstructured": UnstructuredParser,                                 │   │
│  │      "pandas": PandasParser,                                             │   │
│  │      "treesitter": TreeSitterParser                                      │   │
│  │  }                                                                        │   │
│  │                                                                           │   │
│  │  CHUNKER_FACTORY = {                                                      │   │
│  │      "recursive_semantic": RecursiveSemanticChunker,                     │   │
│  │      "row_group": RowGroupChunker,                                       │   │
│  │      "ast_semantic": ASTSemanticChunker,                                 │   │
│  │      "adaptive": AdaptiveChunker                                         │   │
│  │  }                                                                        │   │
│  │                                                                           │   │
│  │  EMBEDDER_FACTORY = {                                                     │   │
│  │      "jinaai-v3": JinaEmbedder,                                          │   │
│  │      "embed-multilingual-v3.0": CohereEmbedder,                          │   │
│  │      "voyage_code": VoyageCodeEmbedder                                   │   │
│  │  }                                                                        │   │
│  │                                                                           │   │
│  │  RERANKER_FACTORY = {                                                     │   │
│  │      "bge-reranker-v2": BGEReranker,                                     │   │
│  │      "cohere-rerank-v3": CohereReranker                                  │   │
│  │  }                                                                        │   │
│  │                                                                           │   │
│  │  LLM_FACTORY = {                                                          │   │
│  │      "gpt-4": OpenAILLM,                                                 │   │
│  │      "gpt-4-vision": OpenAIVisionLLM,                                    │   │
│  │      "claude-3-opus": AnthropicLLM                                       │   │
│  │  }                                                                        │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Strategy Registration

Để thêm một strategy mới vào factory:

```python
# 1. Define the strategy class implementing the interface
class NewChunkerStrategy(BaseChunker):
    def __init__(self, config: dict):
        self.config = config

    def chunk(self, text: str) -> List[Chunk]:
        # Implementation
        pass

# 2. Register to factory
CHUNKER_FACTORY["new_strategy"] = NewChunkerStrategy

# 3. Add validation rules in config schema
# config_schema.py
class ChunkerConfig(BaseModel):
    method: Literal["recursive_semantic", "row_group", "ast_semantic", "adaptive", "new_strategy"]
```

### 3.3 Dynamic Pipeline Construction

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       DYNAMIC PIPELINE CONSTRUCTION                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Pipeline Config (JSON)                                                          │
│         │                                                                        │
│         ▼                                                                        │
│  ┌─────────────────┐                                                            │
│  │ PipelineBuilder │                                                            │
│  │                 │                                                            │
│  │  build(config)  │                                                            │
│  └────────┬────────┘                                                            │
│           │                                                                      │
│           ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  For each step in config:                                                │    │
│  │                                                                          │    │
│  │  1. Get step config (e.g., config["chunker"]["text"])                   │    │
│  │  2. Extract method (e.g., "recursive_semantic")                         │    │
│  │  3. Lookup in factory: CHUNKER_FACTORY["recursive_semantic"]            │    │
│  │  4. Instantiate with step config                                        │    │
│  │  5. Add to pipeline.steps[]                                             │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│           │                                                                      │
│           ▼                                                                      │
│  ┌─────────────────┐                                                            │
│  │    Pipeline     │                                                            │
│  │    Instance     │                                                            │
│  │                 │                                                            │
│  │  steps = [      │                                                            │
│  │    ParserStep,  │                                                            │
│  │    ChunkerStep, │                                                            │
│  │    EmbedderStep,│                                                            │
│  │    IndexerStep  │                                                            │
│  │  ]              │                                                            │
│  └─────────────────┘                                                            │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Builder Implementation Pattern:**

```python
class PipelineBuilder:
    def build_ingestion_pipeline(self, config: IngestionConfig) -> IngestionPipeline:
        steps = []

        # Step 1: Parser
        parser = self._build_parser(config.parser)
        steps.append(ParserStep(parser))

        # Step 2: Content Router
        router = ContentRouter(config.parser)
        steps.append(RouterStep(router))

        # Step 3: Chunker (based on content type)
        chunkers = self._build_chunkers(config.chunker)
        steps.append(ChunkerStep(chunkers))

        # Step 4: Embedder
        embedders = self._build_embedders(config.embedding)
        steps.append(EmbedderStep(embedders))

        # Step 5: Indexer
        indexer = self._build_indexer(config.indexing)
        steps.append(IndexerStep(indexer))

        return IngestionPipeline(steps=steps, config=config)

    def build_retrieval_pipeline(self, config: RetrievalConfig) -> RetrievalPipeline:
        steps = []

        # Step 1: Query Processor (optional)
        if config.prompt_processing.enabled:
            processor = self._build_query_processor(config.prompt_processing)
            steps.append(QueryProcessorStep(processor))

        # Step 2: Embedder
        embedder = self._build_query_embedder(config)
        steps.append(QueryEmbedderStep(embedder))

        # Step 3: Searcher
        searcher = self._build_searcher(config.search)
        steps.append(SearcherStep(searcher))

        # Step 4: Reranker (optional)
        if config.reranking.enabled:
            reranker = self._build_reranker(config.reranking)
            steps.append(RerankerStep(reranker))

        # Step 5: LLM
        llm = self._build_llm(config.llm)
        steps.append(LLMStep(llm))

        return RetrievalPipeline(steps=steps, config=config)
```

---

## 4. Pipeline Executor

### 4.1 Execution Model

Pipeline Executor chịu trách nhiệm chạy tuần tự các steps trong pipeline. Output của step trước trở thành input của step sau.

**Key Principles:**
- **Sequential Execution**: Các steps chạy tuần tự, không có parallelism trong một pipeline
- **No Inter-Step Queue**: Không sử dụng queue giữa các steps trong cùng một pipeline
- **Stateless Processing**: Mỗi step là stateless, dễ retry và debug
- **Context Passing**: Pipeline context được truyền qua tất cả steps

### 4.2 Step Orchestration

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           STEP ORCHESTRATION                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  PipelineContext:                                                               │
│  {                                                                              │
│    "job_id": "job_001",                                                         │
│    "kb_id": "kb_001",                                                           │
│    "user_context": { "user_id": "u1", "tenant_id": "t1" },                      │
│    "document_id": "doc_001",                                                    │
│    "current_step": 0,                                                           │
│    "step_outputs": {},                                                          │
│    "metadata": {}                                                               │
│  }                                                                              │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────┐     │
│  │                         EXECUTION LOOP                                  │     │
│  │                                                                         │     │
│  │  for step in pipeline.steps:                                           │     │
│  │      │                                                                  │     │
│  │      ▼                                                                  │     │
│  │  ┌─────────────────┐                                                   │     │
│  │  │ Get input from  │── From previous step output or initial input      │     │
│  │  │ context         │                                                   │     │
│  │  └────────┬────────┘                                                   │     │
│  │           │                                                             │     │
│  │           ▼                                                             │     │
│  │  ┌─────────────────┐                                                   │     │
│  │  │  Execute step   │── step.execute(input, context)                    │     │
│  │  └────────┬────────┘                                                   │     │
│  │           │                                                             │     │
│  │      ┌────┴────┐                                                        │     │
│  │      │         │                                                        │     │
│  │   Success    Error                                                      │     │
│  │      │         │                                                        │     │
│  │      ▼         ▼                                                        │     │
│  │  Store output  Handle error                                             │     │
│  │  in context    (retry/fail)                                             │     │
│  │      │         │                                                        │     │
│  │      ▼         ▼                                                        │     │
│  │  Update step   Update status                                            │     │
│  │  counter       in DB                                                    │     │
│  └────────────────────────────────────────────────────────────────────────┘     │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Error Handling & Recovery

| Error Type | Handling Strategy | Retry Policy |
|------------|-------------------|--------------|
| **Transient Error** (network, timeout) | Retry with exponential backoff | Max 3 retries, backoff: 1s, 2s, 4s |
| **Validation Error** | Fail immediately, mark document as error | No retry |
| **Resource Error** (OOM, disk full) | Fail immediately, alert ops | No retry |
| **Service Error** (embedding API down) | Retry with circuit breaker | Max 5 retries, circuit opens after 3 consecutive failures |
| **Partial Failure** (some chunks fail) | Continue with successful chunks, log failures | Retry failed chunks only |

**Error Recovery Flow:**

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           ERROR RECOVERY FLOW                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Step Execution Error                                                            │
│         │                                                                        │
│         ▼                                                                        │
│  ┌─────────────────┐                                                            │
│  │ Classify Error  │                                                            │
│  └────────┬────────┘                                                            │
│           │                                                                      │
│      ┌────┴────────────────────┬───────────────────────┐                        │
│      │                         │                       │                        │
│  Transient               Validation              Resource/Fatal                  │
│      │                         │                       │                        │
│      ▼                         ▼                       ▼                        │
│  ┌───────────┐          ┌───────────┐          ┌───────────┐                    │
│  │ Check     │          │ Log error │          │ Log error │                    │
│  │ retry     │          │ Mark doc  │          │ Alert ops │                    │
│  │ count     │          │ as ERROR  │          │ Mark doc  │                    │
│  └─────┬─────┘          └───────────┘          │ as ERROR  │                    │
│        │                                        └───────────┘                    │
│   ┌────┴────┐                                                                    │
│   │         │                                                                    │
│ < Max    >= Max                                                                  │
│   │         │                                                                    │
│   ▼         ▼                                                                    │
│ Retry    Fail job                                                               │
│ with    (move to DLQ)                                                           │
│ backoff                                                                          │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Dead Letter Queue (DLQ) Handling:**
- Failed jobs sau max retries được move vào DLQ
- DLQ jobs được review manually hoặc auto-retry sau 1 hour
- Admin có thể re-queue DLQ jobs từ management UI

---

## 5. Ingestion Pipeline Definition

### 5.1 Pipeline Steps

| Step | Component | Required | Description |
|------|-----------|----------|-------------|
| 1 | **Parser** | Yes | Extract content từ file (PDF, DOCX, Image, Audio, etc.) |
| 2 | **Content Router** | Yes | Detect content type (text, table, code, mixed) và route đến chunker phù hợp |
| 3 | **Chunker** | Yes | Chia content thành chunks theo strategy (recursive, row_group, AST, etc.) |
| 4 | **Embedder** | Yes | Generate embedding vectors cho chunks |
| 5 | **Indexer** | Yes | Index chunks vào Milvus (vector) và Elasticsearch (fulltext) |

### 5.2 Step Dependencies & Constraints

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      INGESTION STEP DEPENDENCIES                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌────────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐        │
│  │   Parser   │────▶│  Content   │────▶│  Chunker   │────▶│  Embedder  │        │
│  │            │     │  Router    │     │            │     │            │        │
│  └────────────┘     └────────────┘     └────────────┘     └────────────┘        │
│        │                  │                  │                  │               │
│        │                  │                  │                  │               │
│        ▼                  ▼                  ▼                  ▼               │
│  Output:            Output:            Output:            Output:               │
│  - raw_text         - content_type     - chunks[]        - vectors[]           │
│  - metadata         - routing_info     - chunk_metadata  - chunk_ids           │
│                                                                │               │
│                                                                ▼               │
│                                                         ┌────────────┐         │
│                                                         │  Indexer   │         │
│                                                         │            │         │
│                                                         └────────────┘         │
│                                                                │               │
│                                                                ▼               │
│                                                         Output:                │
│                                                         - indexed_count        │
│                                                         - milvus_ids           │
│                                                         - es_ids               │
│                                                                                  │
│  Constraints:                                                                   │
│  • Parser output format must match Router expected input                       │
│  • Chunker strategy determined by Content Router output                        │
│  • Embedding model must be consistent across KB (same dimension)               │
│  • Indexer receives both chunks and vectors                                    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 5.3 Sequence Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     INGESTION PIPELINE SEQUENCE                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Worker         Parser        Router        Chunker       Embedder      Indexer │
│    │              │             │             │              │             │    │
│    │──get job─────│             │             │             │              │    │
│    │              │             │             │              │             │    │
│    │──parse(doc)──▶             │             │              │             │    │
│    │              │             │             │              │             │    │
│    │◀──text,meta──│             │             │              │             │    │
│    │              │             │             │              │             │    │
│    │──route(text)───────────────▶             │              │             │    │
│    │              │             │             │              │             │    │
│    │◀──content_type,routing_info│             │              │             │    │
│    │              │             │             │              │             │    │
│    │──chunk(text,type)────────────────────────▶              │             │    │
│    │              │             │             │              │             │    │
│    │◀──chunks[]───────────────────────────────│              │             │    │
│    │              │             │             │              │             │    │
│    │──embed(chunks)───────────────────────────────────────────▶            │    │
│    │              │             │             │              │             │    │
│    │◀──vectors[]──────────────────────────────────────────────│            │    │
│    │              │             │             │              │             │    │
│    │──index(chunks,vectors)─────────────────────────────────────────────────▶   │
│    │              │             │             │              │             │    │
│    │◀──indexed_ids──────────────────────────────────────────────────────────│   │
│    │              │             │             │              │             │    │
│    │──update DB───│             │             │              │             │    │
│    │  (status=    │             │             │              │             │    │
│    │   completed) │             │             │              │             │    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Retrieval Pipeline Definition

### 6.1 Pipeline Steps

| Step | Component | Required | Description |
|------|-----------|----------|-------------|
| 1 | **Query Processor** | No | Rewrite/expand query (HyDE, query expansion, etc.) |
| 2 | **Embedder** | Yes | Generate embedding vector cho query |
| 3 | **Searcher** | Yes | Search trong Milvus + Elasticsearch, fusion với RRF |
| 4 | **Reranker** | No | Rerank results với cross-encoder model |
| 5 | **LLM** | Yes | Generate answer từ context + query |

### 6.2 Optional vs Required Steps

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      RETRIEVAL PIPELINE OPTIONS                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Minimal Pipeline (fast, simple):                                               │
│  ┌────────────┐     ┌────────────┐     ┌────────────┐                          │
│  │  Embedder  │────▶│  Searcher  │────▶│    LLM     │                          │
│  └────────────┘     └────────────┘     └────────────┘                          │
│                                                                                  │
│  Full Pipeline (comprehensive, higher quality):                                  │
│  ┌────────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐       │
│  │   Query    │────▶│  Embedder  │────▶│  Searcher  │────▶│  Reranker  │──▶LLM │
│  │ Processor  │     │            │     │            │     │            │       │
│  └────────────┘     └────────────┘     └────────────┘     └────────────┘       │
│                                                                                  │
│  Configuration Options:                                                          │
│  • prompt_processing.enabled: false → Skip Query Processor                      │
│  • reranking.enabled: false → Skip Reranker                                     │
│  • search.type: "semantic" → Only Milvus, no ES                                 │
│  • search.type: "keyword" → Only ES, no Milvus                                  │
│  • search.type: "hybrid" → Both + RRF fusion                                    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 6.3 Sequence Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     RETRIEVAL PIPELINE SEQUENCE                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Worker      QueryProc      Embedder      Searcher      Reranker       LLM      │
│    │            │             │             │              │            │       │
│    │──get job───│             │             │              │            │       │
│    │            │             │             │              │            │       │
│    │──process───▶ (optional)  │             │              │            │       │
│    │            │             │             │              │            │       │
│    │◀──expanded_query         │             │              │            │       │
│    │            │             │             │              │            │       │
│    │──embed(query)────────────▶             │              │            │       │
│    │            │             │             │              │            │       │
│    │◀──query_vector───────────│             │              │            │       │
│    │            │             │             │              │            │       │
│    │──search(vector,filters)────────────────▶              │            │       │
│    │            │             │             │              │            │       │
│    │◀──results[]────────────────────────────│              │            │       │
│    │            │             │             │              │            │       │
│    │──rerank(results)─────────────────────────────────────▶ (optional)  │       │
│    │            │             │             │              │            │       │
│    │◀──reranked_results────────────────────────────────────│            │       │
│    │            │             │             │              │            │       │
│    │──generate(context,query)───────────────────────────────────────────▶       │
│    │            │             │             │              │            │       │
│    │◀──answer───────────────────────────────────────────────────────────│       │
│    │            │             │             │              │            │       │
│    │──return response         │             │              │            │       │
│                                                                                  │
│  Notes:                                                                          │
│  • Permission filter applied in Searcher step                                   │
│  • is_active filter applied in Searcher step                                    │
│  • Context window management in LLM step                                        │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Queue Architecture

### 7.1 Queue Design

Hệ thống sử dụng **2 queues chính** để tách biệt workload:

| Queue | Technology | Purpose | Consumer |
|-------|------------|---------|----------|
| **Ingestion Queue** | Redis Streams | Document processing jobs | Ingestion Workers |
| **Retrieval Queue** | Redis Streams | Query processing jobs | Retrieval Workers |

**Design Rationale:**
- **2 Queues Only**: Đơn giản hóa operations, mỗi pipeline có queue riêng
- **No Inter-Step Queue**: Workers xử lý sequential, giảm complexity và latency
- **Redis Streams**: Lightweight, persistent, support consumer groups cho horizontal scaling

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           QUEUE ARCHITECTURE                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│                    ┌───────────────────────────────────────────┐                 │
│                    │              REDIS STREAMS                 │                 │
│                    │                                           │                 │
│  API Server        │   ┌───────────────────────────────────┐  │    Workers      │
│  ┌─────────┐       │   │        ingestion_queue            │  │   ┌─────────┐  │
│  │ Upload  │──XADD─┼──▶│  • stream: rag:ingestion         │──┼──▶│Ingestion│  │
│  │ Handler │       │   │  • consumer_group: ingest_workers │  │   │ Worker  │  │
│  └─────────┘       │   └───────────────────────────────────┘  │   └─────────┘  │
│                    │                                           │                 │
│  ┌─────────┐       │   ┌───────────────────────────────────┐  │   ┌─────────┐  │
│  │ Query   │──XADD─┼──▶│        retrieval_queue            │──┼──▶│Retrieval│  │
│  │ Handler │       │   │  • stream: rag:retrieval          │  │   │ Worker  │  │
│  └─────────┘       │   │  • consumer_group: retrieval_workers│  │   └─────────┘  │
│                    │   └───────────────────────────────────┘  │                 │
│                    │                                           │                 │
│                    └───────────────────────────────────────────┘                 │
│                                                                                  │
│  Benefits:                                                                       │
│  • Non-blocking uploads (user không cần chờ processing)                         │
│  • Horizontal scaling workers khi load tăng                                     │
│  • Retry mechanism cho failed jobs                                              │
│  • Job cancellation support                                                     │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Message Schema

**Ingestion Queue Message:**

```json
{
  "job_id": "job_001",
  "request_id": "request_001",
  "document_ids": ["doc_hash_1", "doc_hash_2"],
  "kb_id": "kb_001",
  "pipeline_config_id": "pipeline_001",
  "user_context": {
    "user_id": "user_001",
    "tenant_id": "tenant_001"
  },
  "priority": "normal",
  "created_at": "2026-02-02T10:00:00Z"
}
```

**Retrieval Queue Message:**

```json
{
  "job_id": "query_001",
  "query": "What was Q3 revenue?",
  "kb_id": "kb_001",
  "pipeline_config_id": "retrieval_pipeline_001",
  "user_context": {
    "user_id": "user_001",
    "tenant_id": "tenant_001",
    "groups": ["finance", "management"]
  },
  "options": {
    "stream": true,
    "include_sources": true
  },
  "created_at": "2026-02-02T10:00:00Z"
}
```

### 7.3 Worker Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           WORKER LIFECYCLE                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌───────────┐                                                                  │
│  │   START   │                                                                  │
│  └─────┬─────┘                                                                  │
│        │                                                                        │
│        ▼                                                                        │
│  ┌───────────────────┐                                                          │
│  │ Register Consumer │── XGROUP CREATE (if not exists)                          │
│  │ Group             │                                                          │
│  └─────────┬─────────┘                                                          │
│            │                                                                    │
│            ▼                                                                    │
│  ┌───────────────────┐◀─────────────────────────────────────┐                  │
│  │    XREADGROUP     │── Block until message available      │                  │
│  │    (blocking)     │                                      │                  │
│  └─────────┬─────────┘                                      │                  │
│            │                                                │                  │
│            ▼                                                │                  │
│  ┌───────────────────┐                                      │                  │
│  │   Receive Job     │                                      │                  │
│  └─────────┬─────────┘                                      │                  │
│            │                                                │                  │
│            ▼                                                │                  │
│  ┌───────────────────┐                                      │                  │
│  │ Query DB: Status  │                                      │                  │
│  └─────────┬─────────┘                                      │                  │
│            │                                                │                  │
│       ┌────┴────┐                                           │                  │
│       │         │                                           │                  │
│   cancelled   pending                                       │                  │
│       │         │                                           │                  │
│       ▼         ▼                                           │                  │
│     XACK    ┌───────────────────┐                          │                  │
│       │     │ Update status:    │                          │                  │
│       │     │ processing        │                          │                  │
│       │     └─────────┬─────────┘                          │                  │
│       │               │                                     │                  │
│       │               ▼                                     │                  │
│       │     ┌───────────────────┐                          │                  │
│       │     │ Execute Pipeline  │                          │                  │
│       │     └─────────┬─────────┘                          │                  │
│       │               │                                     │                  │
│       │          ┌────┴────┐                                │                  │
│       │          │         │                                │                  │
│       │       Success    Error                              │                  │
│       │          │         │                                │                  │
│       │          ▼         ▼                                │                  │
│       │     completed    error                              │                  │
│       │          │         │                                │                  │
│       │          ▼         ▼                                │                  │
│       │     Update DB   Update DB                           │                  │
│       │          │         │                                │                  │
│       └──────────┴────┬────┘                                │                  │
│                       │                                     │                  │
│                       ▼                                     │                  │
│                     XACK ───────────────────────────────────┘                  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Job Status State Machine:**

```
pending ──▶ processing ──▶ completed
    │           │
    │           ▼
    ▼         error
cancelled       │
                ▼
            retry (back to pending)
                │
                ▼
            dead_letter (after max retries)
```

---

## 8. Config Versioning & Migration

### Config Versioning Strategy

Khi user thay đổi pipeline config cho KB đã có dữ liệu:

| Scenario | Action | Rationale |
|----------|--------|-----------|
| **Change embedding model** | Require full re-index | Different dimensions, incompatible vectors |
| **Change chunk size** | Require full re-index | Chunks structure changes completely |
| **Change search weights** | No re-index needed | Runtime configuration |
| **Enable/disable reranker** | No re-index needed | Retrieval-time only |
| **Change LLM model** | No re-index needed | Generation-time only |

### Config Version Tracking

```sql
-- Mỗi KB lưu active config version
-- Mỗi document lưu config version được dùng để ingest

CREATE TABLE pipeline_configs (
    id UUID PRIMARY KEY,
    kb_id UUID REFERENCES knowledge_bases(id),
    version INT NOT NULL,
    config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    requires_reindex BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Document tracks config version
ALTER TABLE uploaded_documents
ADD COLUMN ingested_with_config_id UUID REFERENCES pipeline_configs(id);
```

### Migration Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        CONFIG MIGRATION FLOW                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  User updates pipeline config                                                   │
│         │                                                                        │
│         ▼                                                                        │
│  ┌─────────────────┐                                                            │
│  │ Detect changes  │                                                            │
│  └────────┬────────┘                                                            │
│           │                                                                      │
│      ┌────┴────────────────┐                                                    │
│      │                     │                                                    │
│  Breaking change     Non-breaking                                               │
│  (embedding, chunk)  (search, rerank, llm)                                      │
│      │                     │                                                    │
│      ▼                     ▼                                                    │
│  ┌─────────────────┐  ┌─────────────────┐                                       │
│  │ Mark config     │  │ Activate new    │                                       │
│  │ requires_reindex│  │ config directly │                                       │
│  └────────┬────────┘  └─────────────────┘                                       │
│           │                                                                      │
│           ▼                                                                      │
│  ┌─────────────────┐                                                            │
│  │ Show warning to │                                                            │
│  │ user: "Re-index │                                                            │
│  │ required"       │                                                            │
│  └────────┬────────┘                                                            │
│           │                                                                      │
│           ▼                                                                      │
│  User confirms → Queue re-index job for all documents in KB                     │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Dependencies

### Internal Dependencies

| Component | Depends On | Purpose |
|-----------|-----------|---------|
| Pipeline Builder | Component Factories | Build pipeline steps |
| Pipeline Executor | Pipeline Builder, Step Implementations | Execute pipeline |
| Queue Consumer | Redis Client | Receive jobs |
| Config Validator | Pydantic Schemas | Validate configs |

### External Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| Redis | 7.x | Message queue (Redis Streams) |
| PostgreSQL | 15+ | Config storage, job tracking |
| Pydantic | 2.x | Config validation |

### Cross-Document References

| Reference | Document | Section |
|-----------|----------|---------|
| Processing Components | [DD-02-processing-components.md] | All sections |
| Database Schema | [DD-04-data-architecture.md] | Section 2: PostgreSQL Schema |
| RBAC for permission filtering | [DD-05-data-governance.md] | Section 1: Access Control |
| Upload Handler integration | [DD-03-platform-services.md] | Section 2: Document Upload Handler |

---

*Document Version: 1.0*
*Last Updated: 2026-02-02*
