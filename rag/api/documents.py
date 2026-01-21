"""Document API endpoints."""

from fastapi import APIRouter, UploadFile, File, Query, Depends
from schema.rag import DocumentListResponse, DocumentUploadResponse, OriginType
from rag.document_service import DocumentService
from rag.minio_client import minio_client

router = APIRouter(prefix="/documents", tags=["documents"])


def get_service() -> DocumentService:
    return DocumentService(minio_client)


@router.get("", response_model=DocumentListResponse)
def list_documents(
    origin_type: OriginType | None = Query(None, description="Filter: sync hoặc upload"),
    knowledge_base_id: str | None = Query(None, description="Filter theo knowledge base"),
    prefix: str | None = Query(None, description="Filter theo path prefix"),
    service: DocumentService = Depends(get_service)
):
    """Lấy danh sách tài liệu trong SSOT"""
    return service.list_documents(origin_type, knowledge_base_id, prefix)


@router.post("/upload", response_model=DocumentUploadResponse)
def upload_document(
    knowledge_base_id: str = Query(..., description="ID của knowledge base"),
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_service)
):
    """Upload file vào SSOT"""
    content = file.file.read()
    doc = service.upload_document(content, file.filename, knowledge_base_id, file.content_type)
    return DocumentUploadResponse(path=doc.path, filename=doc.filename, size=doc.size)
