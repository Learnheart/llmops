"""Pydantic schemas for RAG Service API."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Component Schemas
# ============================================================================

class ComponentInfo(BaseModel):
    """Component information schema."""
    name: str
    description: str
    category: str
    config_schema: Dict[str, Any] = Field(default_factory=dict)


class ComponentListResponse(BaseModel):
    """Response for listing components."""
    parsers: List[ComponentInfo] = Field(default_factory=list)
    chunkers: List[ComponentInfo] = Field(default_factory=list)
    embedders: List[ComponentInfo] = Field(default_factory=list)
    indexers: List[ComponentInfo] = Field(default_factory=list)
    searchers: List[ComponentInfo] = Field(default_factory=list)
    optimizers: List[ComponentInfo] = Field(default_factory=list)


class CategoryComponentsResponse(BaseModel):
    """Response for listing components in a category."""
    category: str
    components: List[ComponentInfo]
    count: int


# ============================================================================
# Pipeline Configuration Schemas
# ============================================================================

class ParserConfig(BaseModel):
    """Parser configuration."""
    type: str = "auto"
    extract_images: bool = False
    extract_tables: bool = True
    ocr_enabled: bool = False
    ocr_language: str = "eng"


class ChunkerConfig(BaseModel):
    """Chunker configuration."""
    type: str = "recursive"
    chunk_size: int = 512
    chunk_overlap: int = 50
    separators: Optional[List[str]] = None


class EmbedderConfig(BaseModel):
    """Embedder configuration."""
    type: str = "openai"
    model: Optional[str] = None
    batch_size: int = 100


class IndexerConfig(BaseModel):
    """Indexer configuration."""
    type: str = "milvus"
    collection_name: Optional[str] = None
    index_type: str = "IVF_FLAT"
    metric_type: str = "COSINE"


class SearcherConfig(BaseModel):
    """Searcher configuration."""
    type: str = "hybrid"
    semantic_weight: float = 0.7
    fulltext_weight: float = 0.3
    top_k: int = 20


class OptimizerConfig(BaseModel):
    """Single optimizer configuration."""
    type: str
    # Common options
    threshold: Optional[float] = None
    limit: Optional[int] = None
    model: Optional[str] = None
    similarity_threshold: Optional[float] = None
    top_k: Optional[int] = None


class IngestionPipelineConfig(BaseModel):
    """Full ingestion pipeline configuration."""
    parser: ParserConfig = Field(default_factory=ParserConfig)
    chunker: ChunkerConfig = Field(default_factory=ChunkerConfig)
    embedder: EmbedderConfig = Field(default_factory=EmbedderConfig)
    indexer: IndexerConfig = Field(default_factory=IndexerConfig)


class RetrievalPipelineConfig(BaseModel):
    """Full retrieval pipeline configuration."""
    embedder: EmbedderConfig = Field(default_factory=EmbedderConfig)
    searcher: SearcherConfig = Field(default_factory=SearcherConfig)
    optimizers: List[OptimizerConfig] = Field(default_factory=list)


# ============================================================================
# Pipeline Validation Schemas
# ============================================================================

class PipelineValidateRequest(BaseModel):
    """Request for validating pipeline config."""
    pipeline_type: str = Field(..., pattern="^(ingestion|retrieval)$")
    config: Dict[str, Any]


class ValidationError(BaseModel):
    """Single validation error."""
    field: str
    message: str


class PipelineValidateResponse(BaseModel):
    """Response for pipeline validation."""
    valid: bool
    errors: List[ValidationError] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# ============================================================================
# Ingestion Schemas
# ============================================================================

class DocumentInput(BaseModel):
    """Document input for ingestion."""
    storage_path: str = Field(..., description="Path to document in MinIO")
    filename: str
    metadata: Optional[Dict[str, Any]] = None


class IngestionRequest(BaseModel):
    """Request for document ingestion."""
    user_id: str = Field(..., min_length=1, max_length=255)
    knowledge_base_id: str
    documents: List[DocumentInput]
    config: IngestionPipelineConfig = Field(default_factory=IngestionPipelineConfig)


class DocumentResult(BaseModel):
    """Result for a single document ingestion."""
    document_id: str
    filename: str
    status: str
    chunks_created: int = 0
    error: Optional[str] = None


class IngestionResponse(BaseModel):
    """Response for ingestion request."""
    run_id: str
    status: str
    documents_processed: int
    total_chunks_created: int
    results: List[DocumentResult]
    metrics: Dict[str, Any] = Field(default_factory=dict)


class BatchIngestionRequest(BaseModel):
    """Request for batch document ingestion."""
    user_id: str = Field(..., min_length=1, max_length=255)
    knowledge_base_id: str
    documents: List[DocumentInput]
    config: IngestionPipelineConfig = Field(default_factory=IngestionPipelineConfig)
    async_mode: bool = False


# ============================================================================
# Retrieval Schemas
# ============================================================================

class RetrievalRequest(BaseModel):
    """Request for document retrieval."""
    user_id: str = Field(..., min_length=1, max_length=255)
    knowledge_base_id: str
    query: str = Field(..., min_length=1)
    config: RetrievalPipelineConfig = Field(default_factory=RetrievalPipelineConfig)
    top_k: int = Field(default=5, ge=1, le=100)


class ChunkResult(BaseModel):
    """Single chunk result from retrieval."""
    id: str
    content: str
    score: float
    document_id: str
    document_filename: Optional[str] = None
    chunk_index: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RetrievalResponse(BaseModel):
    """Response for retrieval request."""
    run_id: str
    query: str
    results: List[ChunkResult]
    total_results: int
    metrics: Dict[str, Any] = Field(default_factory=dict)


class BatchRetrievalRequest(BaseModel):
    """Request for batch retrieval."""
    user_id: str = Field(..., min_length=1, max_length=255)
    knowledge_base_id: str
    queries: List[str] = Field(..., min_length=1)
    config: RetrievalPipelineConfig = Field(default_factory=RetrievalPipelineConfig)
    top_k: int = Field(default=5, ge=1, le=100)


class BatchQueryResult(BaseModel):
    """Result for a single query in batch."""
    query: str
    results: List[ChunkResult]
    total_results: int


class BatchRetrievalResponse(BaseModel):
    """Response for batch retrieval."""
    run_id: str
    queries_processed: int
    results: List[BatchQueryResult]
    metrics: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Pipeline Run Schemas
# ============================================================================

class PipelineRunResponse(BaseModel):
    """Pipeline run record response."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    knowledge_base_id: Optional[str]
    pipeline_type: str
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    metrics: Optional[Dict[str, Any]]
    created_at: datetime


class PipelineRunListResponse(BaseModel):
    """Response for listing pipeline runs."""
    runs: List[PipelineRunResponse]
    count: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# Knowledge Base Schemas
# ============================================================================

class KnowledgeBaseCreate(BaseModel):
    """Request for creating knowledge base."""
    user_id: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    default_ingestion_config: Optional[Dict[str, Any]] = None
    default_retrieval_config: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class KnowledgeBaseResponse(BaseModel):
    """Knowledge base response."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    description: Optional[str]
    document_count: int
    chunk_count: int
    created_at: datetime
    updated_at: Optional[datetime]


# ============================================================================
# Health Check Schemas
# ============================================================================

class HealthResponse(BaseModel):
    """Basic health check response."""
    status: str
    service: str
    version: str


class StorageStatus(BaseModel):
    """Storage system status."""
    name: str
    status: str
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class DetailedHealthResponse(BaseModel):
    """Detailed health check response."""
    status: str
    service: str
    version: str
    uptime_seconds: float
    storage: Dict[str, StorageStatus]
