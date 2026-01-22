"""Document service for SSOT management."""

from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import or_

from db.minio import MinioClient
from models.document import Document, OriginType
from models.document_permission import DocumentPermission, Permission
from schema.rag import DocumentResponse, DocumentListResponse, DocumentUploadResponse, RemoteFile


class DocumentService:
    """Service quản lý documents trong SSOT."""

    def __init__(self, minio: MinioClient, db: Session):
        self.minio = minio
        self.db = db

    def list_documents(
        self,
        tenant_id: UUID,
        knowledge_base_id: str | None = None,
        origin_type: OriginType | None = None,
    ) -> DocumentListResponse:
        """Lấy danh sách documents mà tenant có quyền truy cập."""

        # Documents được share cho tenant
        shared_doc_ids = (
            self.db.query(DocumentPermission.document_id)
            .filter(DocumentPermission.tenant_id == tenant_id)
            .subquery()
        )

        # Documents thuộc tenant HOẶC được share
        query = self.db.query(Document).filter(
            or_(
                Document.tenant_id == tenant_id,
                Document.id.in_(shared_doc_ids)
            )
        )

        if knowledge_base_id:
            query = query.filter(Document.knowledge_base_id == knowledge_base_id)
        if origin_type:
            query = query.filter(Document.origin_type == origin_type)

        docs = query.all()
        return DocumentListResponse(
            documents=[DocumentResponse.model_validate(d) for d in docs],
            total=len(docs)
        )

    def upload_document(
        self,
        content: bytes,
        filename: str,
        tenant_id: UUID,
        owner_id: UUID,
        knowledge_base_id: str,
        content_type: str | None = None,
        shared_with: list[UUID] | None = None,
    ) -> DocumentUploadResponse:
        """Upload file vào SSOT + lưu metadata vào DB."""

        # Upload to MinIO
        storage_path = f"uploads/{tenant_id}/{knowledge_base_id}/{filename}"
        self.minio.upload(content, storage_path, content_type)

        # Save metadata to DB
        doc = Document(
            tenant_id=tenant_id,
            owner_id=owner_id,
            knowledge_base_id=knowledge_base_id,
            filename=filename,
            storage_path=storage_path,
            file_size=len(content),
            content_type=content_type,
            origin_type=OriginType.UPLOAD,
        )
        self.db.add(doc)
        self.db.flush()

        # Add permissions for shared tenants
        if shared_with:
            for target_tenant_id in shared_with:
                perm = DocumentPermission(
                    document_id=doc.id,
                    tenant_id=target_tenant_id,
                    permission=Permission.READ,
                )
                self.db.add(perm)

        self.db.commit()

        return DocumentUploadResponse(
            id=doc.id,
            filename=doc.filename,
            storage_path=doc.storage_path,
            file_size=doc.file_size,
        )

    def sync_file(
        self,
        tenant_id: UUID,
        owner_id: UUID,
        source_type: str,
        remote_file: RemoteFile,
        content: bytes,
    ) -> Document:
        """Sync file từ external source (internal job only)."""

        storage_path = f"sync/{tenant_id}/{source_type}/{remote_file.path}"
        self.minio.upload(content, storage_path, remote_file.content_type)

        doc = Document(
            tenant_id=tenant_id,
            owner_id=owner_id,
            knowledge_base_id=source_type,
            filename=remote_file.filename,
            storage_path=storage_path,
            file_size=len(content),
            content_type=remote_file.content_type,
            origin_type=OriginType.SYNC,
            source_type=source_type,
        )
        self.db.add(doc)
        self.db.commit()

        return doc
