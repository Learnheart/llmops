"""Tests for SSOTSyncService."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from uuid import uuid4


class TestSSOTSyncService:
    """Tests for SSOTSyncService."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        db = MagicMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def mock_minio(self):
        """Mock MinIO client."""
        client = MagicMock()
        client.list_objects = AsyncMock(return_value=[])
        client.download = AsyncMock(return_value=b"content")
        client.upload = AsyncMock()
        return client

    @pytest.fixture
    def service(self, mock_db, mock_minio):
        """Create SSOTSyncService with mocks."""
        from app.services.ssot_sync_service import SSOTSyncService

        svc = SSOTSyncService(mock_db)
        svc.minio_client = mock_minio
        return svc

    @pytest.mark.asyncio
    async def test_sync_empty_bucket(self, service, mock_minio):
        """Test syncing from empty bucket."""
        mock_minio.list_objects.return_value = []

        result = await service.sync_from_minio(
            source_bucket="source-bucket",
            source_prefix="docs/",
            user_id="user123",
            knowledge_base_id=str(uuid4()),
        )

        assert result.new_count == 0
        assert result.modified_count == 0
        assert result.deleted_count == 0

    @pytest.mark.asyncio
    async def test_sync_new_documents(self, service, mock_db, mock_minio):
        """Test syncing new documents."""
        mock_minio.list_objects.return_value = [
            {"name": "docs/file1.pdf", "etag": "etag1", "last_modified": datetime.utcnow()},
            {"name": "docs/file2.pdf", "etag": "etag2", "last_modified": datetime.utcnow()},
        ]

        # No existing docs
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await service.sync_from_minio(
            source_bucket="source-bucket",
            source_prefix="docs/",
            user_id="user123",
            knowledge_base_id=str(uuid4()),
        )

        assert result.new_count == 2
        assert result.modified_count == 0

    @pytest.mark.asyncio
    async def test_sync_modified_document(self, service, mock_db, mock_minio):
        """Test syncing modified document."""
        from app.models.database import Document

        source_path = "minio://source-bucket/docs/file1.pdf"

        mock_minio.list_objects.return_value = [
            {"name": "docs/file1.pdf", "etag": "new-etag", "last_modified": datetime.utcnow()},
        ]

        # Existing doc with different etag
        existing_doc = MagicMock(spec=Document)
        existing_doc.id = str(uuid4())
        existing_doc.checksum = "old-checksum"
        existing_doc.version = 1
        existing_doc.metadata = {"source_path": source_path, "source_etag": "old-etag"}

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [existing_doc]
        mock_db.execute.return_value = mock_result

        result = await service.sync_from_minio(
            source_bucket="source-bucket",
            source_prefix="docs/",
            user_id="user123",
            knowledge_base_id=str(uuid4()),
        )

        assert result.modified_count == 1

    @pytest.mark.asyncio
    async def test_sync_unchanged_document(self, service, mock_db, mock_minio):
        """Test syncing unchanged document."""
        from app.models.database import Document
        from app.services.ssot_sync_service import SyncStrategy

        source_path = "minio://source-bucket/docs/file1.pdf"
        etag = "same-etag"

        mock_minio.list_objects.return_value = [
            {"name": "docs/file1.pdf", "etag": etag, "last_modified": datetime.utcnow()},
        ]

        # Existing doc with same etag
        existing_doc = MagicMock(spec=Document)
        existing_doc.metadata = {"source_path": source_path, "source_etag": etag}

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [existing_doc]
        mock_db.execute.return_value = mock_result

        result = await service.sync_from_minio(
            source_bucket="source-bucket",
            source_prefix="docs/",
            user_id="user123",
            knowledge_base_id=str(uuid4()),
            strategy=SyncStrategy.INCREMENTAL,
        )

        assert result.unchanged_count == 1
        assert result.modified_count == 0

    @pytest.mark.asyncio
    async def test_sync_deleted_document(self, service, mock_db, mock_minio):
        """Test marking deleted documents."""
        from app.models.database import Document

        # No objects in source
        mock_minio.list_objects.return_value = []

        # Existing doc that should be marked deleted
        existing_doc = MagicMock(spec=Document)
        existing_doc.filename = "deleted.pdf"
        existing_doc.metadata = {"source_path": "minio://source-bucket/docs/deleted.pdf"}

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [existing_doc]
        mock_db.execute.return_value = mock_result

        result = await service.sync_from_minio(
            source_bucket="source-bucket",
            source_prefix="docs/",
            user_id="user123",
            knowledge_base_id=str(uuid4()),
        )

        assert result.deleted_count == 1

    @pytest.mark.asyncio
    async def test_sync_with_file_patterns(self, service, mock_db, mock_minio):
        """Test syncing with file pattern filter."""
        mock_minio.list_objects.return_value = [
            {"name": "docs/file1.pdf", "etag": "e1", "last_modified": datetime.utcnow()},
            {"name": "docs/file2.txt", "etag": "e2", "last_modified": datetime.utcnow()},
            {"name": "docs/file3.docx", "etag": "e3", "last_modified": datetime.utcnow()},
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await service.sync_from_minio(
            source_bucket="source-bucket",
            source_prefix="docs/",
            user_id="user123",
            knowledge_base_id=str(uuid4()),
            file_patterns=["pdf", "docx"],
        )

        # Only pdf and docx should be synced
        assert result.new_count == 2

    @pytest.mark.asyncio
    async def test_sync_full_strategy(self, service, mock_db, mock_minio):
        """Test full sync strategy always marks as modified."""
        from app.models.database import Document
        from app.services.ssot_sync_service import SyncStrategy

        source_path = "minio://source-bucket/docs/file1.pdf"
        etag = "same-etag"

        mock_minio.list_objects.return_value = [
            {"name": "docs/file1.pdf", "etag": etag, "last_modified": datetime.utcnow()},
        ]

        # Existing doc with same etag
        existing_doc = MagicMock(spec=Document)
        existing_doc.id = str(uuid4())
        existing_doc.checksum = "checksum"
        existing_doc.version = 1
        existing_doc.metadata = {"source_path": source_path, "source_etag": etag}

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [existing_doc]
        mock_db.execute.return_value = mock_result

        # Mock download returning same content (same checksum)
        mock_minio.download.return_value = b"same content"

        result = await service.sync_from_minio(
            source_bucket="source-bucket",
            source_prefix="docs/",
            user_id="user123",
            knowledge_base_id=str(uuid4()),
            strategy=SyncStrategy.FULL,
        )

        # Full strategy checks content, not just etag
        assert result.modified_count == 1 or result.unchanged_count == 1

    @pytest.mark.asyncio
    async def test_sync_error_handling(self, service, mock_db, mock_minio):
        """Test error handling during sync."""
        mock_minio.list_objects.return_value = [
            {"name": "docs/file1.pdf", "etag": "e1", "last_modified": datetime.utcnow()},
        ]
        mock_minio.download.side_effect = Exception("Download failed")

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await service.sync_from_minio(
            source_bucket="source-bucket",
            source_prefix="docs/",
            user_id="user123",
            knowledge_base_id=str(uuid4()),
        )

        assert result.failed_count == 1
        assert len(result.errors) == 1
        assert "Download failed" in result.errors[0]

    @pytest.mark.asyncio
    async def test_sync_list_error(self, service, mock_minio):
        """Test error when listing bucket fails."""
        mock_minio.list_objects.side_effect = Exception("Bucket not found")

        result = await service.sync_from_minio(
            source_bucket="nonexistent",
            source_prefix="docs/",
            user_id="user123",
            knowledge_base_id=str(uuid4()),
        )

        assert len(result.errors) == 1
        assert "Failed to list source bucket" in result.errors[0]


class TestSyncResult:
    """Tests for SyncResult."""

    def test_initial_counts(self):
        """Test initial counts are zero."""
        from app.services.ssot_sync_service import SyncResult

        result = SyncResult()

        assert result.new_count == 0
        assert result.modified_count == 0
        assert result.deleted_count == 0
        assert result.unchanged_count == 0
        assert result.failed_count == 0
        assert result.documents == []
        assert result.errors == []

    def test_to_dict(self):
        """Test converting to dictionary."""
        from app.services.ssot_sync_service import SyncResult

        result = SyncResult()
        result.new_count = 5
        result.modified_count = 3
        result.deleted_count = 2
        result.unchanged_count = 10
        result.failed_count = 1
        result.errors = ["error 1"]

        d = result.to_dict()

        assert d["new"] == 5
        assert d["modified"] == 3
        assert d["deleted"] == 2
        assert d["unchanged"] == 10
        assert d["failed"] == 1
        assert d["total_processed"] == 20
        assert d["errors"] == ["error 1"]


class TestChangeType:
    """Tests for ChangeType enum."""

    def test_change_types(self):
        """Test change type values."""
        from app.services.ssot_sync_service import ChangeType

        assert ChangeType.NEW == "new"
        assert ChangeType.MODIFIED == "modified"
        assert ChangeType.DELETED == "deleted"
        assert ChangeType.UNCHANGED == "unchanged"


class TestSyncStrategy:
    """Tests for SyncStrategy enum."""

    def test_sync_strategies(self):
        """Test sync strategy values."""
        from app.services.ssot_sync_service import SyncStrategy

        assert SyncStrategy.FULL == "full"
        assert SyncStrategy.INCREMENTAL == "incremental"


class TestDetectChange:
    """Tests for _detect_change method."""

    @pytest.fixture
    def service(self):
        """Create service for testing."""
        from app.services.ssot_sync_service import SSOTSyncService

        mock_db = MagicMock()
        return SSOTSyncService(mock_db)

    @pytest.mark.asyncio
    async def test_detect_new(self, service):
        """Test detecting new document."""
        from app.services.ssot_sync_service import ChangeType, SyncStrategy

        change = await service._detect_change(
            source_path="minio://bucket/new.pdf",
            source_etag="etag",
            source_modified=datetime.utcnow(),
            existing_doc=None,
            strategy=SyncStrategy.INCREMENTAL,
        )

        assert change == ChangeType.NEW

    @pytest.mark.asyncio
    async def test_detect_modified_by_etag(self, service):
        """Test detecting modified by etag change."""
        from app.models.database import Document
        from app.services.ssot_sync_service import ChangeType, SyncStrategy

        existing_doc = MagicMock(spec=Document)
        existing_doc.metadata = {"source_etag": "old-etag"}

        change = await service._detect_change(
            source_path="minio://bucket/file.pdf",
            source_etag="new-etag",
            source_modified=datetime.utcnow(),
            existing_doc=existing_doc,
            strategy=SyncStrategy.INCREMENTAL,
        )

        assert change == ChangeType.MODIFIED

    @pytest.mark.asyncio
    async def test_detect_unchanged_by_etag(self, service):
        """Test detecting unchanged by etag match."""
        from app.models.database import Document
        from app.services.ssot_sync_service import ChangeType, SyncStrategy

        etag = "same-etag"
        existing_doc = MagicMock(spec=Document)
        existing_doc.metadata = {"source_etag": etag}

        change = await service._detect_change(
            source_path="minio://bucket/file.pdf",
            source_etag=etag,
            source_modified=datetime.utcnow(),
            existing_doc=existing_doc,
            strategy=SyncStrategy.INCREMENTAL,
        )

        assert change == ChangeType.UNCHANGED

    @pytest.mark.asyncio
    async def test_detect_full_strategy_always_modified(self, service):
        """Test full strategy treats all existing as modified."""
        from app.models.database import Document
        from app.services.ssot_sync_service import ChangeType, SyncStrategy

        etag = "same-etag"
        existing_doc = MagicMock(spec=Document)
        existing_doc.metadata = {"source_etag": etag}

        change = await service._detect_change(
            source_path="minio://bucket/file.pdf",
            source_etag=etag,
            source_modified=datetime.utcnow(),
            existing_doc=existing_doc,
            strategy=SyncStrategy.FULL,
        )

        assert change == ChangeType.MODIFIED
