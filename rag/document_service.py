"""Document service for SSOT management."""

from datetime import datetime, timezone
from schema.rag import DocumentInfo, DocumentListResponse, OriginType, RemoteFile
from rag.minio_client import MinioClient


class DocumentService:
    """Service quản lý documents trong SSOT"""

    def __init__(self, minio: MinioClient):
        self.minio = minio

    def list_documents(
        self,
        origin_type: OriginType | None = None,
        knowledge_base_id: str | None = None,
        prefix: str | None = None
    ) -> DocumentListResponse:
        """Lấy danh sách tài liệu trong SSOT"""

        scan_prefix = prefix or self._build_prefix(origin_type, knowledge_base_id)
        objects = self.minio.list_objects(scan_prefix)
        documents = [self._to_document_info(obj) for obj in objects]

        return DocumentListResponse(documents=documents, total=len(documents))

    def upload_document(
        self,
        content: bytes,
        filename: str,
        knowledge_base_id: str,
        content_type: str | None = None
    ) -> DocumentInfo:
        """Upload file vào SSOT"""

        path = f"uploads/{knowledge_base_id}/{filename}"
        self.minio.upload(content, path, content_type)

        return DocumentInfo(
            path=path,
            filename=filename,
            size=len(content),
            origin_type=OriginType.UPLOAD,
            source_type=None,
            last_modified=datetime.now(timezone.utc),
            content_type=content_type
        )

    def sync_file(self, source_type: str, remote_file: RemoteFile, content: bytes) -> DocumentInfo:
        """Sync một file từ external source (internal job only)"""

        path = f"sync/{source_type}/{remote_file.path}"
        self.minio.upload(content, path, remote_file.content_type)

        return DocumentInfo(
            path=path,
            filename=remote_file.filename,
            size=len(content),
            origin_type=OriginType.SYNC,
            source_type=source_type,
            last_modified=remote_file.modified_at,
            content_type=remote_file.content_type
        )

    def _build_prefix(self, origin_type: OriginType | None, knowledge_base_id: str | None) -> str:
        if origin_type == OriginType.SYNC:
            return "sync/"
        if origin_type == OriginType.UPLOAD:
            return f"uploads/{knowledge_base_id}/" if knowledge_base_id else "uploads/"
        return ""

    def _to_document_info(self, obj) -> DocumentInfo:
        path = obj.object_name
        is_sync = path.startswith("sync/")
        parts = path.split("/")

        return DocumentInfo(
            path=path,
            filename=parts[-1],
            size=obj.size,
            origin_type=OriginType.SYNC if is_sync else OriginType.UPLOAD,
            source_type=parts[1] if is_sync and len(parts) > 1 else None,
            last_modified=obj.last_modified,
            content_type=obj.content_type
        )
