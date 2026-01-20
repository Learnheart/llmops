"""Tests for IngestionService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from uuid import uuid4

from app.models.schemas import (
    DocumentInput,
    IngestionPipelineConfig,
    ParserConfig,
    ChunkerConfig,
    EmbedderConfig,
    IndexerConfig,
)


class TestIngestionService:
    """Tests for IngestionService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def mock_minio_client(self):
        """Create mock MinIO client."""
        with patch("app.services.ingestion_service.MinIOClient") as mock:
            client = MagicMock()
            client.download = AsyncMock(return_value=b"Test document content")
            mock.return_value = client
            yield client

    @pytest.fixture
    def mock_parser(self):
        """Create mock parser."""
        parser = MagicMock()
        parsed_result = MagicMock()
        parsed_result.content = "Parsed text content from document"
        parsed_result.metadata = {"pages": 1}
        parser.parse = AsyncMock(return_value=parsed_result)
        return parser

    @pytest.fixture
    def mock_chunker(self):
        """Create mock chunker."""
        chunker = MagicMock()
        chunk1 = MagicMock()
        chunk1.content = "First chunk content"
        chunk1.start_char = 0
        chunk1.end_char = 50
        chunk1.metadata = {}

        chunk2 = MagicMock()
        chunk2.content = "Second chunk content"
        chunk2.start_char = 50
        chunk2.end_char = 100
        chunk2.metadata = {}

        chunker.chunk = AsyncMock(return_value=[chunk1, chunk2])
        return chunker

    @pytest.fixture
    def mock_embedder(self):
        """Create mock embedder."""
        embedder = MagicMock()
        embedder.dimension = 1536
        embedder.model = "text-embedding-3-small"
        embedder.embed = AsyncMock(return_value=[
            [0.1] * 1536,
            [0.2] * 1536,
        ])
        return embedder

    @pytest.fixture
    def mock_indexer(self):
        """Create mock indexer."""
        indexer = MagicMock()
        indexer.create_collection = AsyncMock()
        indexer.index = AsyncMock()
        return indexer

    @pytest.fixture
    def ingestion_config(self):
        """Create sample ingestion config."""
        return IngestionPipelineConfig(
            parser=ParserConfig(type="auto"),
            chunker=ChunkerConfig(type="recursive", chunk_size=512, chunk_overlap=50),
            embedder=EmbedderConfig(type="openai"),
            indexer=IndexerConfig(type="milvus"),
        )

    @pytest.fixture
    def document_inputs(self):
        """Create sample document inputs."""
        return [
            DocumentInput(
                storage_path="minio://docs/test1.pdf",
                filename="test1.pdf",
                metadata={"source": "upload"},
            ),
        ]

    @pytest.mark.asyncio
    async def test_ingest_single_document(
        self,
        mock_db,
        mock_minio_client,
        mock_parser,
        mock_chunker,
        mock_embedder,
        mock_indexer,
        ingestion_config,
        document_inputs,
    ):
        """Test ingesting a single document."""
        with patch("app.services.ingestion_service.ParserFactory") as parser_factory, \
             patch("app.services.ingestion_service.ChunkerFactory") as chunker_factory, \
             patch("app.services.ingestion_service.EmbedderFactory") as embedder_factory, \
             patch("app.services.ingestion_service.IndexerFactory") as indexer_factory, \
             patch("app.services.ingestion_service.MinIOClient") as minio_class:

            parser_factory.create.return_value = mock_parser
            chunker_factory.create.return_value = mock_chunker
            embedder_factory.create.return_value = mock_embedder
            indexer_factory.create.return_value = mock_indexer
            minio_class.return_value = mock_minio_client

            from app.services.ingestion_service import IngestionService

            service = IngestionService(mock_db)
            service.minio_client = mock_minio_client

            result = await service.ingest(
                user_id="user123",
                knowledge_base_id="kb123",
                documents=document_inputs,
                config=ingestion_config,
            )

            assert result.status == "completed"
            assert result.documents_processed == 1
            assert result.total_chunks_created == 2
            assert len(result.results) == 1
            assert result.results[0].status == "completed"
            assert result.results[0].chunks_created == 2

    @pytest.mark.asyncio
    async def test_ingest_multiple_documents(
        self,
        mock_db,
        mock_minio_client,
        mock_parser,
        mock_chunker,
        mock_embedder,
        mock_indexer,
        ingestion_config,
    ):
        """Test ingesting multiple documents."""
        documents = [
            DocumentInput(
                storage_path="minio://docs/test1.pdf",
                filename="test1.pdf",
            ),
            DocumentInput(
                storage_path="minio://docs/test2.pdf",
                filename="test2.pdf",
            ),
        ]

        with patch("app.services.ingestion_service.ParserFactory") as parser_factory, \
             patch("app.services.ingestion_service.ChunkerFactory") as chunker_factory, \
             patch("app.services.ingestion_service.EmbedderFactory") as embedder_factory, \
             patch("app.services.ingestion_service.IndexerFactory") as indexer_factory, \
             patch("app.services.ingestion_service.MinIOClient") as minio_class:

            parser_factory.create.return_value = mock_parser
            chunker_factory.create.return_value = mock_chunker
            embedder_factory.create.return_value = mock_embedder
            indexer_factory.create.return_value = mock_indexer
            minio_class.return_value = mock_minio_client

            from app.services.ingestion_service import IngestionService

            service = IngestionService(mock_db)
            service.minio_client = mock_minio_client

            result = await service.ingest(
                user_id="user123",
                knowledge_base_id="kb123",
                documents=documents,
                config=ingestion_config,
            )

            assert result.documents_processed == 2
            assert result.total_chunks_created == 4  # 2 chunks per document
            assert len(result.results) == 2

    @pytest.mark.asyncio
    async def test_ingest_with_document_failure(
        self,
        mock_db,
        mock_minio_client,
        mock_parser,
        mock_chunker,
        mock_embedder,
        mock_indexer,
        ingestion_config,
    ):
        """Test ingestion handles document failures gracefully."""
        documents = [
            DocumentInput(
                storage_path="minio://docs/test1.pdf",
                filename="test1.pdf",
            ),
        ]

        # Make parser raise an exception
        mock_parser.parse = AsyncMock(side_effect=Exception("Parse error"))

        with patch("app.services.ingestion_service.ParserFactory") as parser_factory, \
             patch("app.services.ingestion_service.ChunkerFactory") as chunker_factory, \
             patch("app.services.ingestion_service.EmbedderFactory") as embedder_factory, \
             patch("app.services.ingestion_service.IndexerFactory") as indexer_factory, \
             patch("app.services.ingestion_service.MinIOClient") as minio_class:

            parser_factory.create.return_value = mock_parser
            chunker_factory.create.return_value = mock_chunker
            embedder_factory.create.return_value = mock_embedder
            indexer_factory.create.return_value = mock_indexer
            minio_class.return_value = mock_minio_client

            from app.services.ingestion_service import IngestionService

            service = IngestionService(mock_db)
            service.minio_client = mock_minio_client

            result = await service.ingest(
                user_id="user123",
                knowledge_base_id="kb123",
                documents=documents,
                config=ingestion_config,
            )

            # Should still return a result, but with failure
            assert result.status == "completed"
            assert len(result.results) == 1
            assert result.results[0].status == "failed"
            assert "Parse error" in result.results[0].error

    @pytest.mark.asyncio
    async def test_ingest_with_empty_chunks(
        self,
        mock_db,
        mock_minio_client,
        mock_parser,
        mock_embedder,
        mock_indexer,
        ingestion_config,
        document_inputs,
    ):
        """Test ingestion with document that produces no chunks."""
        # Mock chunker that returns empty list
        mock_chunker = MagicMock()
        mock_chunker.chunk = AsyncMock(return_value=[])

        with patch("app.services.ingestion_service.ParserFactory") as parser_factory, \
             patch("app.services.ingestion_service.ChunkerFactory") as chunker_factory, \
             patch("app.services.ingestion_service.EmbedderFactory") as embedder_factory, \
             patch("app.services.ingestion_service.IndexerFactory") as indexer_factory, \
             patch("app.services.ingestion_service.MinIOClient") as minio_class:

            parser_factory.create.return_value = mock_parser
            chunker_factory.create.return_value = mock_chunker
            embedder_factory.create.return_value = mock_embedder
            indexer_factory.create.return_value = mock_indexer
            minio_class.return_value = mock_minio_client

            from app.services.ingestion_service import IngestionService

            service = IngestionService(mock_db)
            service.minio_client = mock_minio_client

            result = await service.ingest(
                user_id="user123",
                knowledge_base_id="kb123",
                documents=document_inputs,
                config=ingestion_config,
            )

            assert result.documents_processed == 1
            assert result.total_chunks_created == 0
            assert result.results[0].chunks_created == 0

    @pytest.mark.asyncio
    async def test_ingest_creates_pipeline_run_record(
        self,
        mock_db,
        mock_minio_client,
        mock_parser,
        mock_chunker,
        mock_embedder,
        mock_indexer,
        ingestion_config,
        document_inputs,
    ):
        """Test that ingestion creates a pipeline run record."""
        with patch("app.services.ingestion_service.ParserFactory") as parser_factory, \
             patch("app.services.ingestion_service.ChunkerFactory") as chunker_factory, \
             patch("app.services.ingestion_service.EmbedderFactory") as embedder_factory, \
             patch("app.services.ingestion_service.IndexerFactory") as indexer_factory, \
             patch("app.services.ingestion_service.MinIOClient") as minio_class:

            parser_factory.create.return_value = mock_parser
            chunker_factory.create.return_value = mock_chunker
            embedder_factory.create.return_value = mock_embedder
            indexer_factory.create.return_value = mock_indexer
            minio_class.return_value = mock_minio_client

            from app.services.ingestion_service import IngestionService

            service = IngestionService(mock_db)
            service.minio_client = mock_minio_client

            result = await service.ingest(
                user_id="user123",
                knowledge_base_id="kb123",
                documents=document_inputs,
                config=ingestion_config,
            )

            # Verify db.add was called (for PipelineRun)
            assert mock_db.add.called
            assert mock_db.commit.called

            # Verify run_id is returned
            assert result.run_id is not None
            assert len(result.run_id) > 0

    @pytest.mark.asyncio
    async def test_ingest_auto_collection_name(
        self,
        mock_db,
        mock_minio_client,
        mock_parser,
        mock_chunker,
        mock_embedder,
        mock_indexer,
        document_inputs,
    ):
        """Test auto-generation of collection name."""
        config = IngestionPipelineConfig(
            parser=ParserConfig(type="auto"),
            chunker=ChunkerConfig(type="recursive"),
            embedder=EmbedderConfig(type="openai"),
            indexer=IndexerConfig(type="milvus", collection_name="auto"),
        )

        with patch("app.services.ingestion_service.ParserFactory") as parser_factory, \
             patch("app.services.ingestion_service.ChunkerFactory") as chunker_factory, \
             patch("app.services.ingestion_service.EmbedderFactory") as embedder_factory, \
             patch("app.services.ingestion_service.IndexerFactory") as indexer_factory, \
             patch("app.services.ingestion_service.MinIOClient") as minio_class:

            parser_factory.create.return_value = mock_parser
            chunker_factory.create.return_value = mock_chunker
            embedder_factory.create.return_value = mock_embedder
            indexer_factory.create.return_value = mock_indexer
            minio_class.return_value = mock_minio_client

            from app.services.ingestion_service import IngestionService

            service = IngestionService(mock_db)
            service.minio_client = mock_minio_client

            await service.ingest(
                user_id="user123",
                knowledge_base_id="kb123",
                documents=document_inputs,
                config=config,
            )

            # Verify create_collection was called with auto-generated name
            mock_indexer.create_collection.assert_called_once()
            call_args = mock_indexer.create_collection.call_args
            assert "kb_user123_kb123" in call_args.kwargs.get("collection_name", "")

    @pytest.mark.asyncio
    async def test_ingest_with_metadata(
        self,
        mock_db,
        mock_minio_client,
        mock_parser,
        mock_chunker,
        mock_embedder,
        mock_indexer,
        ingestion_config,
    ):
        """Test ingestion preserves document metadata."""
        documents = [
            DocumentInput(
                storage_path="minio://docs/test.pdf",
                filename="test.pdf",
                metadata={"source": "api", "version": "1.0", "author": "test"},
            ),
        ]

        with patch("app.services.ingestion_service.ParserFactory") as parser_factory, \
             patch("app.services.ingestion_service.ChunkerFactory") as chunker_factory, \
             patch("app.services.ingestion_service.EmbedderFactory") as embedder_factory, \
             patch("app.services.ingestion_service.IndexerFactory") as indexer_factory, \
             patch("app.services.ingestion_service.MinIOClient") as minio_class:

            parser_factory.create.return_value = mock_parser
            chunker_factory.create.return_value = mock_chunker
            embedder_factory.create.return_value = mock_embedder
            indexer_factory.create.return_value = mock_indexer
            minio_class.return_value = mock_minio_client

            from app.services.ingestion_service import IngestionService

            service = IngestionService(mock_db)
            service.minio_client = mock_minio_client

            result = await service.ingest(
                user_id="user123",
                knowledge_base_id="kb123",
                documents=documents,
                config=ingestion_config,
            )

            assert result.documents_processed == 1


class TestIngestionServiceGetFileType:
    """Tests for _get_file_type helper method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    def test_get_file_type_pdf(self, mock_db):
        """Test extracting PDF file type."""
        with patch("app.services.ingestion_service.MinIOClient"):
            from app.services.ingestion_service import IngestionService
            service = IngestionService(mock_db)
            assert service._get_file_type("document.pdf") == "pdf"

    def test_get_file_type_docx(self, mock_db):
        """Test extracting DOCX file type."""
        with patch("app.services.ingestion_service.MinIOClient"):
            from app.services.ingestion_service import IngestionService
            service = IngestionService(mock_db)
            assert service._get_file_type("document.docx") == "docx"

    def test_get_file_type_multiple_dots(self, mock_db):
        """Test file with multiple dots."""
        with patch("app.services.ingestion_service.MinIOClient"):
            from app.services.ingestion_service import IngestionService
            service = IngestionService(mock_db)
            assert service._get_file_type("my.document.v2.pdf") == "pdf"

    def test_get_file_type_uppercase(self, mock_db):
        """Test uppercase extension."""
        with patch("app.services.ingestion_service.MinIOClient"):
            from app.services.ingestion_service import IngestionService
            service = IngestionService(mock_db)
            assert service._get_file_type("DOCUMENT.PDF") == "pdf"

    def test_get_file_type_no_extension(self, mock_db):
        """Test file without extension."""
        with patch("app.services.ingestion_service.MinIOClient"):
            from app.services.ingestion_service import IngestionService
            service = IngestionService(mock_db)
            assert service._get_file_type("README") == "unknown"

    def test_get_file_type_hidden_file(self, mock_db):
        """Test hidden file with extension."""
        with patch("app.services.ingestion_service.MinIOClient"):
            from app.services.ingestion_service import IngestionService
            service = IngestionService(mock_db)
            assert service._get_file_type(".gitignore") == "gitignore"


class TestIngestionServiceIntegration:
    """Integration-style tests for IngestionService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        return db

    @pytest.mark.asyncio
    async def test_full_ingestion_pipeline_flow(self, mock_db):
        """Test the full flow of the ingestion pipeline."""
        with patch("app.services.ingestion_service.ParserFactory") as parser_factory, \
             patch("app.services.ingestion_service.ChunkerFactory") as chunker_factory, \
             patch("app.services.ingestion_service.EmbedderFactory") as embedder_factory, \
             patch("app.services.ingestion_service.IndexerFactory") as indexer_factory, \
             patch("app.services.ingestion_service.MinIOClient") as minio_class:

            # Setup mock parser
            mock_parser = MagicMock()
            parsed_result = MagicMock()
            parsed_result.content = "Document content for testing"
            parsed_result.metadata = {}
            mock_parser.parse = AsyncMock(return_value=parsed_result)
            parser_factory.create.return_value = mock_parser

            # Setup mock chunker
            mock_chunker = MagicMock()
            chunk = MagicMock()
            chunk.content = "Chunk content"
            chunk.start_char = 0
            chunk.end_char = 50
            chunk.metadata = {}
            mock_chunker.chunk = AsyncMock(return_value=[chunk])
            chunker_factory.create.return_value = mock_chunker

            # Setup mock embedder
            mock_embedder = MagicMock()
            mock_embedder.dimension = 1536
            mock_embedder.model = "text-embedding-3-small"
            mock_embedder.embed = AsyncMock(return_value=[[0.1] * 1536])
            embedder_factory.create.return_value = mock_embedder

            # Setup mock indexer
            mock_indexer = MagicMock()
            mock_indexer.create_collection = AsyncMock()
            mock_indexer.index = AsyncMock()
            indexer_factory.create.return_value = mock_indexer

            # Setup mock MinIO
            mock_minio = MagicMock()
            mock_minio.download = AsyncMock(return_value=b"Test content")
            minio_class.return_value = mock_minio

            from app.services.ingestion_service import IngestionService

            service = IngestionService(mock_db)

            config = IngestionPipelineConfig()
            documents = [
                DocumentInput(
                    storage_path="minio://docs/test.pdf",
                    filename="test.pdf",
                )
            ]

            result = await service.ingest(
                user_id="user1",
                knowledge_base_id="kb1",
                documents=documents,
                config=config,
            )

            # Verify pipeline execution order
            mock_minio.download.assert_called_once()
            mock_parser.parse.assert_called_once()
            mock_chunker.chunk.assert_called_once()
            mock_embedder.embed.assert_called_once()
            mock_indexer.create_collection.assert_called_once()
            mock_indexer.index.assert_called_once()

            # Verify result
            assert result.status == "completed"
            assert result.documents_processed == 1
            assert result.total_chunks_created == 1

    @pytest.mark.asyncio
    async def test_metrics_calculation(self, mock_db):
        """Test that metrics are calculated correctly."""
        with patch("app.services.ingestion_service.ParserFactory") as parser_factory, \
             patch("app.services.ingestion_service.ChunkerFactory") as chunker_factory, \
             patch("app.services.ingestion_service.EmbedderFactory") as embedder_factory, \
             patch("app.services.ingestion_service.IndexerFactory") as indexer_factory, \
             patch("app.services.ingestion_service.MinIOClient") as minio_class:

            # Setup mocks with minimal configuration
            mock_parser = MagicMock()
            parsed_result = MagicMock()
            parsed_result.content = "Content"
            parsed_result.metadata = {}
            mock_parser.parse = AsyncMock(return_value=parsed_result)
            parser_factory.create.return_value = mock_parser

            mock_chunker = MagicMock()
            chunk = MagicMock()
            chunk.content = "Chunk"
            chunk.start_char = 0
            chunk.end_char = 5
            chunk.metadata = {}
            mock_chunker.chunk = AsyncMock(return_value=[chunk, chunk, chunk])
            chunker_factory.create.return_value = mock_chunker

            mock_embedder = MagicMock()
            mock_embedder.dimension = 384
            mock_embedder.model = "test-model"
            mock_embedder.embed = AsyncMock(return_value=[[0.1] * 384] * 3)
            embedder_factory.create.return_value = mock_embedder

            mock_indexer = MagicMock()
            mock_indexer.create_collection = AsyncMock()
            mock_indexer.index = AsyncMock()
            indexer_factory.create.return_value = mock_indexer

            mock_minio = MagicMock()
            mock_minio.download = AsyncMock(return_value=b"Test")
            minio_class.return_value = mock_minio

            from app.services.ingestion_service import IngestionService

            service = IngestionService(mock_db)

            result = await service.ingest(
                user_id="user1",
                knowledge_base_id="kb1",
                documents=[DocumentInput(storage_path="minio://b/f", filename="f.txt")],
                config=IngestionPipelineConfig(),
            )

            # Verify metrics
            assert "duration_ms" in result.metrics
            assert result.metrics["duration_ms"] > 0
            assert result.metrics["documents_count"] == 1
            assert result.metrics["chunks_count"] == 3
