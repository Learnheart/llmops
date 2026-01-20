"""Ingestion service for document processing pipeline."""

import hashlib
import time
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.models.database import (
    Document,
    Chunk,
    KnowledgeBase,
    PipelineRun,
    PipelineType,
    PipelineRunStatus,
    DocumentStatus,
)
from app.models.schemas import (
    IngestionRequest,
    IngestionResponse,
    DocumentResult,
    DocumentInput,
    IngestionPipelineConfig,
)
from app.components.parsers.factory import ParserFactory
from app.components.chunkers.factory import ChunkerFactory
from app.components.embedders.factory import EmbedderFactory
from app.components.indexers.factory import IndexerFactory
from app.components.indexers.base import IndexedDocument
from app.clients.minio_client import MinIOClient

settings = get_settings()


class IngestionService:
    """Service for document ingestion pipeline execution."""

    def __init__(self, db: AsyncSession):
        """Initialize ingestion service.

        Args:
            db: Database session
        """
        self.db = db
        self.minio_client = MinIOClient()

    async def ingest(
        self,
        user_id: str,
        knowledge_base_id: str,
        documents: List[DocumentInput],
        config: IngestionPipelineConfig,
    ) -> IngestionResponse:
        """Execute ingestion pipeline.

        Args:
            user_id: User ID
            knowledge_base_id: Knowledge base ID
            documents: Documents to ingest
            config: Pipeline configuration

        Returns:
            IngestionResponse with results
        """
        start_time = time.time()

        # Create pipeline run record
        run = PipelineRun(
            id=str(uuid4()),
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            pipeline_type=PipelineType.INGESTION,
            config=config.model_dump(),
            status=PipelineRunStatus.RUNNING,
            started_at=datetime.utcnow(),
        )
        self.db.add(run)
        await self.db.commit()

        # Initialize components
        parser = ParserFactory.create(config.parser.type)
        chunker = ChunkerFactory.create(config.chunker.type)
        embedder = EmbedderFactory.create(config.embedder.type)
        indexer = IndexerFactory.create(config.indexer.type)

        # Determine collection name
        collection_name = config.indexer.collection_name
        if not collection_name or collection_name == "auto":
            collection_name = f"kb_{user_id}_{knowledge_base_id}"

        # Ensure collection exists
        dimension = embedder.dimension
        await indexer.create_collection(
            collection_name=collection_name,
            dimension=dimension,
            index_type=config.indexer.index_type,
            metric_type=config.indexer.metric_type,
        )

        # Process documents
        results = []
        total_chunks = 0
        documents_processed = 0

        for doc_input in documents:
            try:
                doc_result = await self._process_document(
                    doc_input=doc_input,
                    user_id=user_id,
                    knowledge_base_id=knowledge_base_id,
                    parser=parser,
                    chunker=chunker,
                    embedder=embedder,
                    indexer=indexer,
                    collection_name=collection_name,
                    config=config,
                )

                results.append(doc_result)
                total_chunks += doc_result.chunks_created
                documents_processed += 1

            except Exception as e:
                results.append(
                    DocumentResult(
                        document_id="",
                        filename=doc_input.filename,
                        status="failed",
                        chunks_created=0,
                        error=str(e),
                    )
                )

        # Calculate metrics
        duration_ms = (time.time() - start_time) * 1000

        # Update pipeline run
        run.status = PipelineRunStatus.COMPLETED
        run.completed_at = datetime.utcnow()
        run.result = {
            "documents_processed": documents_processed,
            "total_chunks": total_chunks,
        }
        run.metrics = {
            "duration_ms": round(duration_ms, 2),
            "documents_count": len(documents),
            "chunks_count": total_chunks,
        }
        await self.db.commit()

        return IngestionResponse(
            run_id=run.id,
            status="completed",
            documents_processed=documents_processed,
            total_chunks_created=total_chunks,
            results=results,
            metrics=run.metrics,
        )

    async def _process_document(
        self,
        doc_input: DocumentInput,
        user_id: str,
        knowledge_base_id: str,
        parser,
        chunker,
        embedder,
        indexer,
        collection_name: str,
        config: IngestionPipelineConfig,
    ) -> DocumentResult:
        """Process a single document.

        Args:
            doc_input: Document input
            user_id: User ID
            knowledge_base_id: Knowledge base ID
            parser: Parser instance
            chunker: Chunker instance
            embedder: Embedder instance
            indexer: Indexer instance
            collection_name: Target collection
            config: Pipeline config

        Returns:
            DocumentResult
        """
        # Download document from MinIO
        content = await self.minio_client.download(doc_input.storage_path)

        # Calculate checksum
        checksum = hashlib.sha256(content).hexdigest()

        # Create document record
        doc = Document(
            id=str(uuid4()),
            knowledge_base_id=knowledge_base_id,
            user_id=user_id,
            filename=doc_input.filename,
            file_type=self._get_file_type(doc_input.filename),
            file_size=len(content),
            storage_path=doc_input.storage_path,
            status=DocumentStatus.PROCESSING,
            checksum=checksum,
            metadata=doc_input.metadata,
        )
        self.db.add(doc)
        await self.db.commit()

        try:
            # Parse document
            parsed = await parser.parse(content, doc_input.filename)

            # Chunk content
            chunks = await chunker.chunk(
                text=parsed.content,
                chunk_size=config.chunker.chunk_size,
                chunk_overlap=config.chunker.chunk_overlap,
            )

            if not chunks:
                doc.status = DocumentStatus.INDEXED
                doc.chunk_count = 0
                await self.db.commit()

                return DocumentResult(
                    document_id=doc.id,
                    filename=doc_input.filename,
                    status="completed",
                    chunks_created=0,
                )

            # Generate embeddings
            chunk_texts = [c.content for c in chunks]
            embeddings = await embedder.embed(
                texts=chunk_texts,
                batch_size=config.embedder.batch_size,
            )

            # Prepare for indexing
            indexed_docs = []
            chunk_records = []

            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_id = str(uuid4())

                # Create IndexedDocument
                indexed_docs.append(
                    IndexedDocument(
                        id=chunk_id,
                        content=chunk.content,
                        vector=embedding,
                        metadata={
                            "document_id": doc.id,
                            "filename": doc_input.filename,
                            "chunk_index": i,
                            **(chunk.metadata or {}),
                        },
                    )
                )

                # Create Chunk record
                chunk_record = Chunk(
                    id=chunk_id,
                    document_id=doc.id,
                    content=chunk.content,
                    chunk_index=i,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                    embedding_model=config.embedder.model or embedder.model,
                    metadata=chunk.metadata,
                )
                chunk_records.append(chunk_record)

            # Index in vector store
            await indexer.index(
                documents=indexed_docs,
                collection_name=collection_name,
            )

            # Save chunk records
            for chunk_record in chunk_records:
                self.db.add(chunk_record)

            # Update document status
            doc.status = DocumentStatus.INDEXED
            doc.chunk_count = len(chunks)
            doc.processed_at = datetime.utcnow()
            await self.db.commit()

            return DocumentResult(
                document_id=doc.id,
                filename=doc_input.filename,
                status="completed",
                chunks_created=len(chunks),
            )

        except Exception as e:
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(e)
            await self.db.commit()
            raise

    def _get_file_type(self, filename: str) -> str:
        """Extract file type from filename."""
        if "." in filename:
            return filename.rsplit(".", 1)[-1].lower()
        return "unknown"
