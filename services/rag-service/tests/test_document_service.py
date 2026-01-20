"""Tests for DocumentService."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4


class TestDocumentService:
    """Tests for DocumentService."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        db = MagicMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.execute = AsyncMock()
        db.delete = AsyncMock()
        return db

    @pytest.fixture
    def mock_minio(self):
        """Mock MinIO client."""
        client = MagicMock()
        client.upload = AsyncMock()
        client.download = AsyncMock(return_value=b"content")
        client.delete = AsyncMock()
        return client

    @pytest.fixture
    def service(self, mock_db, mock_minio):
        """Create DocumentService with mocks."""
        from app.services.document_service import DocumentService

        svc = DocumentService(mock_db)
        svc.minio_client = mock_minio
        return svc

    @pytest.mark.asyncio
    async def test_upload_new_document(self, service, mock_db):
        """Test uploading a new document."""
        content = b"test content"
        filename = "test.pdf"
        user_id = "user123"
        kb_id = str(uuid4())

        # Mock no duplicate found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        doc = await service.upload(
            content=content,
            filename=filename,
            user_id=user_id,
            knowledge_base_id=kb_id,
        )

        assert doc is not None
        assert doc.filename == filename
        assert doc.user_id == user_id
        assert doc.source_type == "user_upload"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_upload_duplicate_user_document(self, service, mock_db):
        """Test uploading duplicate user document raises error."""
        from app.services.document_service import DuplicateDocumentError
        from app.models.database import Document

        content = b"test content"
        existing_doc = MagicMock(spec=Document)
        existing_doc.id = str(uuid4())
        existing_doc.filename = "existing.pdf"
        existing_doc.source_type = "user_upload"

        # Mock duplicate found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_doc
        mock_db.execute.return_value = mock_result

        with pytest.raises(DuplicateDocumentError) as exc_info:
            await service.upload(
                content=content,
                filename="test.pdf",
                user_id="user123",
                knowledge_base_id=str(uuid4()),
            )

        assert exc_info.value.existing_doc == existing_doc
        assert exc_info.value.is_ssot is False

    @pytest.mark.asyncio
    async def test_upload_duplicate_ssot_document(self, service, mock_db):
        """Test uploading document that duplicates SSOT raises error with SSOT flag."""
        from app.services.document_service import DuplicateDocumentError
        from app.models.database import Document

        content = b"test content"
        existing_doc = MagicMock(spec=Document)
        existing_doc.id = str(uuid4())
        existing_doc.filename = "synced.pdf"
        existing_doc.source_type = "ssot"

        # Mock SSOT duplicate found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_doc
        mock_db.execute.return_value = mock_result

        with pytest.raises(DuplicateDocumentError) as exc_info:
            await service.upload(
                content=content,
                filename="test.pdf",
                user_id="user123",
                knowledge_base_id=str(uuid4()),
            )

        assert exc_info.value.existing_doc == existing_doc
        assert exc_info.value.is_ssot is True

    @pytest.mark.asyncio
    async def test_check_duplicate_exists(self, service, mock_db):
        """Test checking for duplicates when one exists."""
        from app.models.database import Document

        content = b"test content"
        existing_doc = MagicMock(spec=Document)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_doc
        mock_db.execute.return_value = mock_result

        is_dup, doc = await service.check_duplicate(content, str(uuid4()))

        assert is_dup is True
        assert doc == existing_doc

    @pytest.mark.asyncio
    async def test_check_duplicate_not_exists(self, service, mock_db):
        """Test checking for duplicates when none exists."""
        content = b"test content"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        is_dup, doc = await service.check_duplicate(content, str(uuid4()))

        assert is_dup is False
        assert doc is None

    @pytest.mark.asyncio
    async def test_get_document(self, service, mock_db):
        """Test getting document by ID."""
        from app.models.database import Document

        doc_id = str(uuid4())
        existing_doc = MagicMock(spec=Document)
        existing_doc.id = doc_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_doc
        mock_db.execute.return_value = mock_result

        doc = await service.get_document(doc_id)

        assert doc == existing_doc

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, service, mock_db):
        """Test getting non-existent document."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        doc = await service.get_document(str(uuid4()))

        assert doc is None

    @pytest.mark.asyncio
    async def test_get_document_with_user_filter(self, service, mock_db):
        """Test getting document with user ID filter."""
        from app.models.database import Document

        doc_id = str(uuid4())
        user_id = "user123"
        existing_doc = MagicMock(spec=Document)
        existing_doc.id = doc_id
        existing_doc.user_id = user_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_doc
        mock_db.execute.return_value = mock_result

        doc = await service.get_document(doc_id, user_id=user_id)

        assert doc == existing_doc

    @pytest.mark.asyncio
    async def test_list_documents(self, service, mock_db):
        """Test listing documents in knowledge base."""
        from app.models.database import Document

        kb_id = str(uuid4())
        docs = [MagicMock(spec=Document), MagicMock(spec=Document)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = docs
        mock_db.execute.return_value = mock_result

        result = await service.list_documents(kb_id)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_documents_with_filters(self, service, mock_db):
        """Test listing documents with filters."""
        from app.models.database import Document, DocumentStatus

        kb_id = str(uuid4())
        docs = [MagicMock(spec=Document)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = docs
        mock_db.execute.return_value = mock_result

        result = await service.list_documents(
            knowledge_base_id=kb_id,
            source_type="ssot",
            status=DocumentStatus.INDEXED,
            limit=10,
            offset=0,
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_delete_document(self, service, mock_db, mock_minio):
        """Test deleting a document."""
        from app.models.database import Document

        doc_id = str(uuid4())
        existing_doc = MagicMock(spec=Document)
        existing_doc.id = doc_id
        existing_doc.storage_path = "minio://bucket/path"

        # Mock get_document
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_doc
        mock_db.execute.return_value = mock_result

        result = await service.delete_document(doc_id)

        assert result is True
        mock_minio.delete.assert_called_once()
        mock_db.delete.assert_called_once()
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_delete_document_not_found(self, service, mock_db):
        """Test deleting non-existent document."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.delete_document(str(uuid4()))

        assert result is False

    @pytest.mark.asyncio
    async def test_download_content(self, service, mock_db, mock_minio):
        """Test downloading document content."""
        from app.models.database import Document

        doc_id = str(uuid4())
        existing_doc = MagicMock(spec=Document)
        existing_doc.storage_path = "minio://bucket/path"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_doc
        mock_db.execute.return_value = mock_result

        content = await service.download_content(doc_id)

        assert content == b"content"
        mock_minio.download.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_content_not_found(self, service, mock_db):
        """Test downloading content for non-existent document."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        content = await service.download_content(str(uuid4()))

        assert content is None

    def test_compute_checksum(self, service):
        """Test checksum computation."""
        content = b"test content"
        checksum = service._compute_checksum(content)

        assert len(checksum) == 64  # SHA-256 hex
        # Same content should give same checksum
        assert checksum == service._compute_checksum(content)

    def test_get_file_type(self, service):
        """Test file type extraction."""
        assert service._get_file_type("document.pdf") == "pdf"
        assert service._get_file_type("file.DOCX") == "docx"
        assert service._get_file_type("no_extension") == "unknown"

    def test_get_content_type(self, service):
        """Test MIME type detection."""
        assert service._get_content_type("doc.pdf") == "application/pdf"
        assert service._get_content_type("doc.txt") == "text/plain"
        assert service._get_content_type("doc.unknown") == "application/octet-stream"

    def test_generate_storage_path(self, service):
        """Test storage path generation."""
        path = service._generate_storage_path(
            user_id="user123",
            knowledge_base_id="kb456",
            doc_id="doc789",
            filename="test.pdf",
            version=1,
        )

        assert "tenant-user123" in path
        assert "kb-kb456" in path
        assert "doc-doc789" in path
        assert "v1" in path
        assert "test.pdf" in path


class TestDuplicateDocumentError:
    """Tests for DuplicateDocumentError."""

    def test_error_message_user_upload(self):
        """Test error message for user upload duplicate."""
        from app.services.document_service import DuplicateDocumentError
        from app.models.database import Document

        doc = MagicMock(spec=Document)
        doc.id = "doc123"
        doc.filename = "test.pdf"

        error = DuplicateDocumentError(doc, is_ssot=False)

        assert "đã được upload" in str(error)
        assert "doc123" in str(error)

    def test_error_message_ssot(self):
        """Test error message for SSOT duplicate."""
        from app.services.document_service import DuplicateDocumentError
        from app.models.database import Document

        doc = MagicMock(spec=Document)
        doc.id = "doc123"
        doc.filename = "synced.pdf"

        error = DuplicateDocumentError(doc, is_ssot=True)

        assert "SSOT" in str(error)
        assert "doc123" in str(error)

    def test_error_attributes(self):
        """Test error attributes are set correctly."""
        from app.services.document_service import DuplicateDocumentError
        from app.models.database import Document

        doc = MagicMock(spec=Document)

        error = DuplicateDocumentError(doc, is_ssot=True)

        assert error.existing_doc == doc
        assert error.is_ssot is True
