# RAG Service

Document ingestion and retrieval pipeline service for LLMOps Platform.

## Overview

RAG Service provides a stateless, config-driven pipeline for:
- **Ingestion**: Parse documents → Chunk text → Generate embeddings → Index in vector store
- **Retrieval**: Search with query → Apply optimizers → Return relevant chunks

## Features

### Component Factory Pattern

All pipeline components are pluggable via factory pattern:

| Category | Components |
|----------|------------|
| **Parsers** | auto, pdf, docx, markdown, html, csv, text |
| **Chunkers** | recursive, fixed, sentence, semantic |
| **Embedders** | openai, local (sentence-transformers) |
| **Indexers** | milvus, elasticsearch |
| **Searchers** | semantic, fulltext, hybrid (RRF) |
| **Optimizers** | reranking, score_threshold, deduplication, max_results |

### Stateless Design

- Service processes requests with config provided in each request
- No persistent pipeline configurations stored in service
- LLMOps platform manages pipeline configs and sends them for execution

## API Endpoints

### Components

```
GET  /api/v1/components              # List all components
GET  /api/v1/components/{category}   # List by category
GET  /api/v1/components/{category}/{name}  # Get component info
```

### Pipelines

```
POST /api/v1/pipelines/validate      # Validate pipeline config
GET  /api/v1/pipelines/templates/ingestion   # Get ingestion template
GET  /api/v1/pipelines/templates/retrieval   # Get retrieval template
GET  /api/v1/pipelines/runs          # List pipeline runs
```

### Ingestion

```
POST /api/v1/ingest                  # Ingest documents
POST /api/v1/ingest/batch            # Batch ingestion
GET  /api/v1/ingest/status/{run_id}  # Check status
```

### Retrieval

```
POST /api/v1/retrieve                # Retrieve documents
POST /api/v1/retrieve/batch          # Batch retrieval
POST /api/v1/retrieve/search         # Simple search
```

## Configuration

### Environment Variables

```bash
# Service
SERVICE_NAME=rag-service
SERVICE_PORT=8084

# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=llmops
POSTGRES_PASSWORD=your_password
POSTGRES_DB=llmops

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=your_secret

# Milvus
MILVUS_HOST=milvus
MILVUS_PORT=19530

# Elasticsearch
ELASTICSEARCH_URL=http://elasticsearch:9200

# OpenAI (for embeddings)
OPENAI_API_KEY=sk-your-key
```

## Usage Examples

### Ingest Documents

```bash
curl -X POST http://localhost:8084/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "knowledge_base_id": "kb-uuid",
    "documents": [
      {"storage_path": "minio://docs/file.pdf", "filename": "file.pdf"}
    ],
    "config": {
      "parser": {"type": "auto"},
      "chunker": {"type": "recursive", "chunk_size": 512},
      "embedder": {"type": "openai"},
      "indexer": {"type": "milvus"}
    }
  }'
```

### Retrieve Documents

```bash
curl -X POST http://localhost:8084/api/v1/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "knowledge_base_id": "kb-uuid",
    "query": "What is the return policy?",
    "config": {
      "searcher": {"type": "hybrid", "semantic_weight": 0.7},
      "optimizers": [
        {"type": "reranking"},
        {"type": "score_threshold", "threshold": 0.5},
        {"type": "max_results", "limit": 5}
      ]
    },
    "top_k": 5
  }'
```

## Development

### Setup

```bash
cd services/rag-service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run

```bash
uvicorn app.main:app --reload --port 8084
```

### Test

```bash
pytest tests/ -v
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      RAG SERVICE                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                 API GATEWAY                          │   │
│  │   /components  /pipelines  /ingest  /retrieve        │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              SERVICE LAYER                           │   │
│  │   IngestionService        RetrievalService           │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           COMPONENT FACTORIES                        │   │
│  │  Parsers │ Chunkers │ Embedders │ Indexers          │   │
│  │  Searchers │ Optimizers                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              DATA LAYER                              │   │
│  │  MinIO │ PostgreSQL │ Milvus │ Elasticsearch         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## License

MIT
