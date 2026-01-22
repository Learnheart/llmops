"""Document API endpoints."""

from uuid import UUID
from fastapi import APIRouter, UploadFile, File, Query, Depends, Header
from sqlalchemy.orm import Session

from db.postgres import get_db
from db.minio import minio_client
from models.document import OriginType
from schema.rag import DocumentListResponse, DocumentUploadResponse
from rag.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


def get_service(db: Session = Depends(get_db)) -> DocumentService:
    return DocumentService(minio_client, db)


@router.get("", response_model=DocumentListResponse)
def list_documents(
    tenant_id: UUID = Header(..., alias="X-Tenant-ID"),
    knowledge_base_id: str | None = Query(None),
    origin_type: OriginType | None = Query(None),
    service: DocumentService = Depends(get_service),
):
    """Lấy danh sách documents của tenant."""
    return service.list_documents(tenant_id, knowledge_base_id, origin_type)


@router.post("/upload", response_model=DocumentUploadResponse)
def upload_document(
    tenant_id: UUID = Header(..., alias="X-Tenant-ID"),
    owner_id: UUID = Header(..., alias="X-User-ID"),
    knowledge_base_id: str = Query(...),
    shared_with: list[UUID] | None = Query(None),
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_service),
):
    """Upload document vào SSOT."""
    content = file.file.read()
    return service.upload_document(
        content=content,
        filename=file.filename,
        tenant_id=tenant_id,
        owner_id=owner_id,
        knowledge_base_id=knowledge_base_id,
        content_type=file.content_type,
        shared_with=shared_with,
    )
