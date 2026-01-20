"""SSOT Sync service for synchronizing documents from external sources."""

import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.database import Document, DocumentStatus
from app.clients.minio_client import MinIOClient

settings = get_settings()


class SyncStrategy(str, Enum):
    """Sync strategy types."""
    FULL = "full"           # Scan entire source
    INCREMENTAL = "incremental"  # Only changes since last sync


class ChangeType(str, Enum):
    """Document change types."""
    NEW = "new"
    MODIFIED = "modified"
    DELETED = "deleted"
    UNCHANGED = "unchanged"


class SyncResult:
    """Result of a sync operation."""

    def __init__(self):
        self.new_count = 0
        self.modified_count = 0
        self.deleted_count = 0
        self.unchanged_count = 0
        self.failed_count = 0
        self.documents: List[Dict[str, Any]] = []
        self.errors: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "new": self.new_count,
            "modified": self.modified_count,
            "deleted": self.deleted_count,
            "unchanged": self.unchanged_count,
            "failed": self.failed_count,
            "total_processed": self.new_count + self.modified_count + self.deleted_count + self.unchanged_count,
            "errors": self.errors,
        }


class SSOTSyncService:
    """Service for synchronizing documents from external SSOT sources.

    Supports syncing from:
    - MinIO/S3 buckets
    - (Future: GCS, Azure Blob, SharePoint, HTTP)
    """

    def __init__(self, db: AsyncSession):
        """Initialize SSOT sync service.

        Args:
            db: Database session
        """
        self.db = db
        self.minio_client = MinIOClient()

    async def sync_from_minio(
        self,
        source_bucket: str,
        source_prefix: str,
        user_id: str,
        knowledge_base_id: str,
        strategy: SyncStrategy = SyncStrategy.INCREMENTAL,
        file_patterns: Optional[List[str]] = None,
    ) -> SyncResult:
        """Sync documents from a MinIO bucket.

        Args:
            source_bucket: Source bucket name
            source_prefix: Prefix/folder to sync from
            user_id: User ID
            knowledge_base_id: Target knowledge base ID
            strategy: Sync strategy (full or incremental)
            file_patterns: Optional file extensions to include (e.g., ['pdf', 'docx'])

        Returns:
            SyncResult with sync statistics
        """
        result = SyncResult()

        # List objects in source
        try:
            source_objects = await self.minio_client.list_objects(
                bucket=source_bucket,
                prefix=source_prefix,
                recursive=True,
            )
        except Exception as e:
            result.errors.append(f"Failed to list source bucket: {str(e)}")
            return result

        # Filter by file patterns if specified
        if file_patterns:
            source_objects = [
                obj for obj in source_objects
                if any(obj["name"].lower().endswith(f".{p.lower()}") for p in file_patterns)
            ]

        # Get existing documents in this KB from SSOT
        existing_docs = await self._get_ssot_documents(knowledge_base_id)
        existing_by_source = {doc.metadata.get("source_path"): doc for doc in existing_docs if doc.metadata}

        # Track processed source paths
        processed_paths = set()

        # Process each source object
        for obj in source_objects:
            source_path = f"minio://{source_bucket}/{obj['name']}"
            processed_paths.add(source_path)

            try:
                change_type = await self._detect_change(
                    source_path=source_path,
                    source_etag=obj.get("etag"),
                    source_modified=obj.get("last_modified"),
                    existing_doc=existing_by_source.get(source_path),
                    strategy=strategy,
                )

                if change_type == ChangeType.NEW:
                    await self._sync_new_document(
                        source_bucket=source_bucket,
                        source_object=obj,
                        user_id=user_id,
                        knowledge_base_id=knowledge_base_id,
                    )
                    result.new_count += 1

                elif change_type == ChangeType.MODIFIED:
                    await self._sync_modified_document(
                        source_bucket=source_bucket,
                        source_object=obj,
                        existing_doc=existing_by_source[source_path],
                        user_id=user_id,
                        knowledge_base_id=knowledge_base_id,
                    )
                    result.modified_count += 1

                elif change_type == ChangeType.UNCHANGED:
                    result.unchanged_count += 1

            except Exception as e:
                result.errors.append(f"Failed to sync {obj['name']}: {str(e)}")
                result.failed_count += 1

        # Handle deleted documents (in source but not in processed)
        for source_path, doc in existing_by_source.items():
            if source_path not in processed_paths:
                try:
                    await self._mark_document_deleted(doc)
                    result.deleted_count += 1
                except Exception as e:
                    result.errors.append(f"Failed to mark deleted {doc.filename}: {str(e)}")

        return result

    async def _get_ssot_documents(self, knowledge_base_id: str) -> List[Document]:
        """Get all SSOT documents in a knowledge base."""
        query = (
            select(Document)
            .where(Document.knowledge_base_id == knowledge_base_id)
            .where(Document.source_type == "ssot")
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _detect_change(
        self,
        source_path: str,
        source_etag: Optional[str],
        source_modified: Optional[datetime],
        existing_doc: Optional[Document],
        strategy: SyncStrategy,
    ) -> ChangeType:
        """Detect type of change for a document.

        Args:
            source_path: Path in source
            source_etag: ETag from source
            source_modified: Last modified time
            existing_doc: Existing document record
            strategy: Sync strategy

        Returns:
            ChangeType indicating what action to take
        """
        if existing_doc is None:
            return ChangeType.NEW

        if strategy == SyncStrategy.FULL:
            # In full sync, always check content
            return ChangeType.MODIFIED

        # Incremental: check ETag or last modified
        existing_etag = existing_doc.metadata.get("source_etag") if existing_doc.metadata else None
        existing_modified = existing_doc.metadata.get("source_modified") if existing_doc.metadata else None

        if source_etag and existing_etag:
            if source_etag != existing_etag:
                return ChangeType.MODIFIED
            return ChangeType.UNCHANGED

        if source_modified and existing_modified:
            if str(source_modified) != str(existing_modified):
                return ChangeType.MODIFIED
            return ChangeType.UNCHANGED

        # If can't determine, treat as modified to be safe
        return ChangeType.MODIFIED

    async def _sync_new_document(
        self,
        source_bucket: str,
        source_object: Dict[str, Any],
        user_id: str,
        knowledge_base_id: str,
    ) -> Document:
        """Sync a new document from source."""
        source_path = f"minio://{source_bucket}/{source_object['name']}"
        filename = source_object["name"].split("/")[-1]

        # Download content
        content = await self.minio_client.download(source_path)

        # Compute checksum
        checksum = hashlib.sha256(content).hexdigest()

        # Generate storage path in our bucket
        doc_id = str(uuid4())
        dest_bucket = settings.minio_bucket_documents
        dest_path = f"tenant-{user_id}/kb-{knowledge_base_id}/doc-{doc_id}/v1/{filename}"
        storage_path = f"minio://{dest_bucket}/{dest_path}"

        # Upload to our storage
        await self.minio_client.upload(
            content=content,
            bucket=dest_bucket,
            object_name=dest_path,
        )

        # Create document record
        doc = Document(
            id=doc_id,
            knowledge_base_id=knowledge_base_id,
            user_id=user_id,
            filename=filename,
            file_type=filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown",
            file_size=len(content),
            storage_path=storage_path,
            source_type="ssot",
            status=DocumentStatus.PENDING,
            version=1,
            checksum=checksum,
            metadata={
                "source_path": source_path,
                "source_etag": source_object.get("etag"),
                "source_modified": str(source_object.get("last_modified")),
                "synced_at": datetime.utcnow().isoformat(),
            },
        )

        self.db.add(doc)
        await self.db.commit()

        return doc

    async def _sync_modified_document(
        self,
        source_bucket: str,
        source_object: Dict[str, Any],
        existing_doc: Document,
        user_id: str,
        knowledge_base_id: str,
    ) -> Document:
        """Sync a modified document (create new version)."""
        source_path = f"minio://{source_bucket}/{source_object['name']}"
        filename = source_object["name"].split("/")[-1]

        # Download new content
        content = await self.minio_client.download(source_path)
        new_checksum = hashlib.sha256(content).hexdigest()

        # Check if actually changed
        if new_checksum == existing_doc.checksum:
            # Content same, just update metadata
            existing_doc.metadata = {
                **(existing_doc.metadata or {}),
                "source_etag": source_object.get("etag"),
                "source_modified": str(source_object.get("last_modified")),
                "synced_at": datetime.utcnow().isoformat(),
            }
            await self.db.commit()
            return existing_doc

        # Content changed - create new version
        new_version = existing_doc.version + 1
        dest_bucket = settings.minio_bucket_documents
        dest_path = f"tenant-{user_id}/kb-{knowledge_base_id}/doc-{existing_doc.id}/v{new_version}/{filename}"
        storage_path = f"minio://{dest_bucket}/{dest_path}"

        # Upload new version
        await self.minio_client.upload(
            content=content,
            bucket=dest_bucket,
            object_name=dest_path,
        )

        # Update document record
        existing_doc.version = new_version
        existing_doc.storage_path = storage_path
        existing_doc.file_size = len(content)
        existing_doc.checksum = new_checksum
        existing_doc.status = DocumentStatus.PENDING  # Needs re-processing
        existing_doc.metadata = {
            **(existing_doc.metadata or {}),
            "source_path": source_path,
            "source_etag": source_object.get("etag"),
            "source_modified": str(source_object.get("last_modified")),
            "synced_at": datetime.utcnow().isoformat(),
            "previous_version": new_version - 1,
        }

        await self.db.commit()

        return existing_doc

    async def _mark_document_deleted(self, doc: Document) -> None:
        """Mark a document as deleted (soft delete)."""
        doc.status = DocumentStatus.FAILED  # Or add DELETED status
        doc.metadata = {
            **(doc.metadata or {}),
            "deleted_from_source": True,
            "deleted_at": datetime.utcnow().isoformat(),
        }
        await self.db.commit()
