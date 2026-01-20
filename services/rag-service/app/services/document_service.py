"""Document service for upload and management with deduplication."""

import hashlib
from datetime import datetime
from typing import Optional, List, Tuple
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.database import Document, DocumentStatus
from app.clients.minio_client import MinIOClient

settings = get_settings()


class DuplicateDocumentError(Exception):
    """Raised when attempting to upload a duplicate document."""

    def __init__(self, existing_doc: Document, is_ssot: bool = False):
        self.existing_doc = existing_doc
        self.is_ssot = is_ssot

        if is_ssot:
            message = (
                f"File đã tồn tại từ nguồn đồng bộ (SSOT). "
                f"Document ID: {existing_doc.id}, Filename: {existing_doc.filename}"
            )
        else:
            message = (
                f"File đã được upload trước đó. "
                f"Document ID: {existing_doc.id}, Filename: {existing_doc.filename}"
            )

        super().__init__(message)


class DocumentService:
    """Service for document upload and management with deduplication."""

    def __init__(self, db: AsyncSession):
        """Initialize document service.

        Args:
            db: Database session
        """
        self.db = db
        self.minio_client = MinIOClient()

    async def upload(
        self,
        content: bytes,
        filename: str,
        user_id: str,
        knowledge_base_id: str,
        metadata: Optional[dict] = None,
    ) -> Document:
        """Upload a document with deduplication check.

        Args:
            content: File content as bytes
            filename: Original filename
            user_id: User ID
            knowledge_base_id: Knowledge base ID
            metadata: Optional metadata

        Returns:
            Created Document record

        Raises:
            DuplicateDocumentError: If file already exists (SSOT has priority)
        """
        # Compute checksum
        checksum = self._compute_checksum(content)

        # Check for duplicates
        existing_doc = await self._find_duplicate(checksum, knowledge_base_id)

        if existing_doc:
            is_ssot = existing_doc.source_type == "ssot"
            raise DuplicateDocumentError(existing_doc, is_ssot)

        # Generate storage path
        doc_id = str(uuid4())
        storage_path = self._generate_storage_path(
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            doc_id=doc_id,
            filename=filename,
            version=1,
        )

        # Upload to MinIO
        bucket = settings.minio_bucket_documents
        object_name = storage_path.replace(f"minio://{bucket}/", "")

        await self.minio_client.upload(
            content=content,
            bucket=bucket,
            object_name=object_name,
            content_type=self._get_content_type(filename),
        )

        # Create document record
        doc = Document(
            id=doc_id,
            knowledge_base_id=knowledge_base_id,
            user_id=user_id,
            filename=filename,
            file_type=self._get_file_type(filename),
            file_size=len(content),
            storage_path=storage_path,
            source_type="user_upload",
            status=DocumentStatus.PENDING,
            version=1,
            checksum=checksum,
            metadata=metadata,
        )

        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)

        return doc

    async def _find_duplicate(
        self,
        checksum: str,
        knowledge_base_id: str,
    ) -> Optional[Document]:
        """Find duplicate document by checksum.

        Args:
            checksum: File checksum
            knowledge_base_id: Knowledge base ID

        Returns:
            Existing document if found, None otherwise
        """
        query = (
            select(Document)
            .where(Document.checksum == checksum)
            .where(Document.knowledge_base_id == knowledge_base_id)
            .order_by(
                # SSOT files have priority (sorted first)
                Document.source_type.asc()  # 'ssot' < 'user_upload'
            )
            .limit(1)
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def check_duplicate(
        self,
        content: bytes,
        knowledge_base_id: str,
    ) -> Tuple[bool, Optional[Document]]:
        """Check if content already exists without uploading.

        Args:
            content: File content
            knowledge_base_id: Knowledge base ID

        Returns:
            Tuple of (is_duplicate, existing_document)
        """
        checksum = self._compute_checksum(content)
        existing = await self._find_duplicate(checksum, knowledge_base_id)
        return (existing is not None, existing)

    async def get_document(
        self,
        document_id: str,
        user_id: Optional[str] = None,
    ) -> Optional[Document]:
        """Get document by ID.

        Args:
            document_id: Document ID
            user_id: Optional user ID for access control

        Returns:
            Document if found
        """
        query = select(Document).where(Document.id == document_id)

        if user_id:
            query = query.where(Document.user_id == user_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_documents(
        self,
        knowledge_base_id: str,
        user_id: Optional[str] = None,
        source_type: Optional[str] = None,
        status: Optional[DocumentStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Document]:
        """List documents in a knowledge base.

        Args:
            knowledge_base_id: Knowledge base ID
            user_id: Optional user ID filter
            source_type: Optional source type filter
            status: Optional status filter
            limit: Max results
            offset: Offset for pagination

        Returns:
            List of documents
        """
        query = select(Document).where(Document.knowledge_base_id == knowledge_base_id)

        if user_id:
            query = query.where(Document.user_id == user_id)
        if source_type:
            query = query.where(Document.source_type == source_type)
        if status:
            query = query.where(Document.status == status)

        query = query.order_by(Document.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def delete_document(
        self,
        document_id: str,
        user_id: Optional[str] = None,
    ) -> bool:
        """Delete a document.

        Args:
            document_id: Document ID
            user_id: Optional user ID for access control

        Returns:
            True if deleted
        """
        doc = await self.get_document(document_id, user_id)

        if not doc:
            return False

        # Delete from MinIO
        try:
            await self.minio_client.delete(doc.storage_path)
        except Exception:
            pass  # File may not exist

        # Delete from database (cascades to chunks)
        await self.db.delete(doc)
        await self.db.commit()

        return True

    async def download_content(self, document_id: str) -> Optional[bytes]:
        """Download document content.

        Args:
            document_id: Document ID

        Returns:
            File content as bytes
        """
        doc = await self.get_document(document_id)

        if not doc:
            return None

        return await self.minio_client.download(doc.storage_path)

    def _compute_checksum(self, content: bytes) -> str:
        """Compute SHA-256 checksum of content."""
        return hashlib.sha256(content).hexdigest()

    def _get_file_type(self, filename: str) -> str:
        """Extract file type from filename."""
        if "." in filename:
            return filename.rsplit(".", 1)[-1].lower()
        return "unknown"

    def _get_content_type(self, filename: str) -> str:
        """Get MIME type for filename."""
        ext = self._get_file_type(filename)

        content_types = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "doc": "application/msword",
            "txt": "text/plain",
            "md": "text/markdown",
            "html": "text/html",
            "htm": "text/html",
            "csv": "text/csv",
            "json": "application/json",
            "xml": "application/xml",
        }

        return content_types.get(ext, "application/octet-stream")

    def _generate_storage_path(
        self,
        user_id: str,
        knowledge_base_id: str,
        doc_id: str,
        filename: str,
        version: int,
    ) -> str:
        """Generate storage path for document.

        Format: minio://bucket/tenant-{user_id}/kb-{kb_id}/doc-{doc_id}/v{version}/{filename}
        """
        bucket = settings.minio_bucket_documents
        path = f"tenant-{user_id}/kb-{knowledge_base_id}/doc-{doc_id}/v{version}/{filename}"
        return f"minio://{bucket}/{path}"
