# RAG Document Management Module - Kiến trúc & Thiết kế

## Mục lục

1. [Tổng quan](#1-tổng-quan)
2. [Kiến trúc hệ thống](#2-kiến-trúc-hệ-thống)
3. [Data Models](#3-data-models)
4. [Luồng xử lý](#4-luồng-xử-lý)
5. [Service Layer](#5-service-layer)
6. [API Endpoints](#6-api-endpoints)
7. [Code Structure](#7-code-structure)
8. [Kế hoạch triển khai](#8-kế-hoạch-triển-khai)

---

## 1. Tổng quan

### 1.1. Mục tiêu

Document Management Module là thành phần cốt lõi của hệ thống RAG, chịu trách nhiệm quản lý toàn bộ vòng đời của documents từ khi upload/sync cho đến khi được xử lý và đưa vào hệ thống tìm kiếm.

### 1.2. Phạm vi chức năng

| Chức năng                     | Mô tả                                                                  |
| ----------------------------- | ---------------------------------------------------------------------- |
| **Knowledge Base Management** | Tổ chức documents theo logical containers, binding với pipeline config |
| **Document Lifecycle**        | Quản lý trạng thái, versioning, soft delete                            |
| **Sync Management**           | Đồng bộ từ external sources (GitHub, Confluence, S3...)                |
| **Processing Integration**    | Tích hợp với Ingest Pipeline để xử lý documents                        |
| **Storage Management**        | Quản lý file storage với MinIO, quota, cleanup                         |

### 1.3. Đánh giá hiện trạng

**Đã có:**

- Document model cơ bản với tenant_id, knowledge_base_id
- Document permission cho cross-tenant sharing
- DocumentService với list, upload, sync cơ bản
- BaseAdapter interface và GitHubAdapter
- MinIO basic upload/list

**Cần bổ sung:**

- Knowledge Base model đầy đủ
- Document status tracking và versioning
- Sync Config/Job models
- Event-driven processing integration
- Storage service hoàn chỉnh

---

## 2. Kiến trúc hệ thống

### 2.1. High-level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      DOCUMENT MANAGEMENT SYSTEM                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                           ┌─────────────────┐                               │
│                           │   API Layer     │                               │
│                           │  /documents     │                               │
│                           │  /knowledge-bases│                              │
│                           │  /sync-configs  │                               │
│                           └────────┬────────┘                               │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        SERVICE LAYER                                 │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │    │
│  │  │ KB Service  │  │  Document   │  │    Sync     │  │ Storage   │  │    │
│  │  │             │  │  Service    │  │   Service   │  │ Service   │  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        DATA LAYER                                    │    │
│  │                                                                      │    │
│  │  PostgreSQL:                         MinIO:                          │    │
│  │  ┌─────────────────────────┐        ┌─────────────────────────┐     │    │
│  │  │ • KnowledgeBase         │        │ /{tenant_id}/           │     │    │
│  │  │ • Document              │        │   /{kb_id}/             │     │    │
│  │  │ • DocumentVersion       │        │     /documents/         │     │    │
│  │  │ • SyncConfig            │        │       /{doc_id}/        │     │    │
│  │  │ • SyncJob               │        │         /v{version}/    │     │    │
│  │  │ • DocumentPermission    │        │           file.pdf      │     │    │
│  │  └─────────────────────────┘        └─────────────────────────┘     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      EVENT/QUEUE LAYER                               │    │
│  │                                                                      │    │
│  │  Document Events:                                                    │    │
│  │  • document.uploaded → Trigger Ingest Pipeline                      │    │
│  │  • document.updated  → Re-process if content changed               │    │
│  │  • document.deleted  → Cleanup chunks/vectors                       │    │
│  │  • sync.completed    → Process new/updated files                    │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2. Nguyên tắc thiết kế

1. **Multi-tenant isolation**: Mọi data đều được phân tách theo tenant_id
2. **Event-driven processing**: Document upload tự động trigger ingest pipeline
3. **Soft delete với retention**: Documents được archive trước khi xóa vĩnh viễn
4. **Versioning**: Track lịch sử thay đổi của documents
5. **Idempotent sync**: Sync operations có thể chạy lại mà không gây duplicate

---

## 3. Data Models

### 3.1. Knowledge Base

Logical container cho documents, binding với pipeline config.

| Field              | Type            | Mô tả                 |
| ------------------ | --------------- | --------------------- |
| id                 | UUID            | Primary key           |
| tenant_id          | UUID            | FK → tenants          |
| name               | VARCHAR(255)    | Tên knowledge base    |
| description        | TEXT            | Mô tả                 |
| slug               | VARCHAR(100)    | Unique per tenant     |
| pipeline_config_id | UUID (nullable) | FK → pipeline_configs |
| settings           | JSONB           | Cấu hình KB           |
| document_count     | INT             | Denormalized stats    |
| total_size_bytes   | BIGINT          | Denormalized stats    |
| chunk_count        | INT             | Denormalized stats    |
| created_at         | TIMESTAMP       |                       |
| updated_at         | TIMESTAMP       |                       |
| created_by         | UUID            | FK → users            |

**Settings schema:**

```json
{
  "auto_process": true,
  "allowed_file_types": ["pdf", "docx", "md"],
  "max_file_size_mb": 50,
  "chunk_on_upload": true
}
```

**Indexes:**

- `(tenant_id, slug)` UNIQUE
- `(tenant_id, created_at)`

### 3.2. Document (Enhanced)

| Field                  | Type            | Mô tả                                     |
| ---------------------- | --------------- | ----------------------------------------- |
| id                     | UUID            | Primary key                               |
| tenant_id              | UUID            | FK → tenants                              |
| knowledge_base_id      | UUID            | FK → knowledge_bases                      |
| owner_id               | UUID            | FK → users                                |
| filename               | VARCHAR(255)    | Tên file gốc                              |
| storage_path           | VARCHAR(512)    | Path trong MinIO                          |
| file_size              | BIGINT          | Kích thước file                           |
| content_type           | VARCHAR(100)    | MIME type                                 |
| origin_type            | ENUM            | SYNC / UPLOAD                             |
| source_type            | VARCHAR(50)     | github, confluence, local...              |
| **current_version**    | INT             | Version hiện tại                          |
| **file_hash**          | VARCHAR(64)     | SHA256 của content                        |
| **status**             | ENUM            | pending/processing/active/failed/archived |
| **processing_error**   | TEXT            | Error message nếu failed                  |
| **processed_at**       | TIMESTAMP       | Lần process gần nhất                      |
| **title**              | VARCHAR(500)    | Extracted hoặc user input                 |
| **description**        | TEXT            | Mô tả document                            |
| **metadata**           | JSONB           | Custom metadata                           |
| **sync_config_id**     | UUID (nullable) | FK → sync_configs                         |
| **remote_path**        | VARCHAR(1000)   | Path trong source                         |
| **remote_modified_at** | TIMESTAMP       | Last modified từ source                   |
| **last_synced_at**     | TIMESTAMP       |                                           |
| created_at             | TIMESTAMP       |                                           |
| updated_at             | TIMESTAMP       |                                           |

**Status values:**

- `pending`: Vừa upload, chưa process
- `processing`: Đang chạy ingest pipeline
- `active`: Đã process xong, searchable
- `failed`: Process failed
- `archived`: Soft deleted

**Metadata schema:**

```json
{
  "author": "...",
  "page_count": 50,
  "language": "vi",
  "tags": ["policy", "hr"],
  "custom_field": "value"
}
```

**Indexes:**

- `(tenant_id, knowledge_base_id, status)`
- `(tenant_id, file_hash)` - detect duplicates
- `(sync_config_id, remote_path)` - sync lookup

### 3.3. Document Version

Track lịch sử thay đổi của document.

| Field              | Type         | Mô tả                  |
| ------------------ | ------------ | ---------------------- |
| id                 | UUID         | Primary key            |
| document_id        | UUID         | FK → documents         |
| version            | INT          | Version number         |
| storage_path       | VARCHAR(512) | Path trong MinIO       |
| file_size          | BIGINT       | Kích thước file        |
| file_hash          | VARCHAR(64)  | SHA256                 |
| pipeline_config_id | UUID         | Config dùng để process |
| chunk_count        | INT          | Số chunks              |
| processing_status  | ENUM         | pending/done/failed    |
| change_summary     | TEXT         | Mô tả thay đổi         |
| created_at         | TIMESTAMP    |                        |
| created_by         | UUID         | FK → users             |

**Constraints:**

- `(document_id, version)` UNIQUE

### 3.4. Sync Config

Cấu hình sync từ external source.

| Field             | Type         | Mô tả                     |
| ----------------- | ------------ | ------------------------- |
| id                | UUID         | Primary key               |
| tenant_id         | UUID         | FK → tenants              |
| knowledge_base_id | UUID         | FK → knowledge_bases      |
| name              | VARCHAR(255) | Tên config                |
| source_type       | VARCHAR(50)  | github, confluence, s3... |
| source_config     | JSONB        | Connection config         |
| include_patterns  | JSONB        | File patterns to include  |
| exclude_patterns  | JSONB        | File patterns to exclude  |
| sync_mode         | ENUM         | manual/webhook/scheduled  |
| schedule_cron     | VARCHAR(100) | Cron expression           |
| is_active         | BOOLEAN      | Config có active không    |
| last_sync_at      | TIMESTAMP    |                           |
| last_sync_status  | ENUM         | success/failed/running    |
| created_at        | TIMESTAMP    |                           |
| updated_at        | TIMESTAMP    |                           |
| created_by        | UUID         | FK → users                |

**Source config example (GitHub):**

```json
{
  "repo": "owner/repo",
  "branch": "main",
  "token_secret_ref": "secret://github_token"
}
```

**Patterns example:**

```json
{
  "include_patterns": ["*.md", "docs/**/*.pdf"],
  "exclude_patterns": ["**/test/**", "*.tmp"]
}
```

### 3.5. Sync Job

Track từng lần chạy sync.

| Field          | Type            | Mô tả                                      |
| -------------- | --------------- | ------------------------------------------ |
| id             | UUID            | Primary key                                |
| sync_config_id | UUID            | FK → sync_configs                          |
| tenant_id      | UUID            | FK → tenants                               |
| status         | ENUM            | pending/running/completed/failed/cancelled |
| trigger_type   | ENUM            | manual/scheduled/webhook                   |
| triggered_by   | UUID (nullable) | User nếu manual                            |
| files_found    | INT             | Số files tìm thấy                          |
| files_added    | INT             | Số files mới                               |
| files_updated  | INT             | Số files cập nhật                          |
| files_deleted  | INT             | Số files xóa                               |
| files_skipped  | INT             | Số files bỏ qua                            |
| files_failed   | INT             | Số files lỗi                               |
| error_message  | TEXT            | Error message                              |
| error_details  | JSONB           | Chi tiết từng file failed                  |
| started_at     | TIMESTAMP       |                                            |
| completed_at   | TIMESTAMP       |                                            |
| created_at     | TIMESTAMP       |                                            |

---

## 4. Luồng xử lý

### 4.1. Document Status Flow

```
  UPLOAD FLOW:

    User Upload
        │
        ▼
   ┌─────────┐     auto_process=true    ┌────────────┐
   │ PENDING │ ──────────────────────── │ PROCESSING │
   └─────────┘                          └─────┬──────┘
        │                                     │
        │ auto_process=false                  ├── success
        │                                     │      │
        ▼                                     │      ▼
   Wait for manual                            │  ┌────────┐
   trigger                                    │  │ ACTIVE │
                                              │  └────────┘
                                              │
                                              └── failure
                                                    │
                                                    ▼
                                               ┌────────┐
                                               │ FAILED │
                                               └────┬───┘
                                                    │
                                                    │ retry
                                                    └─────────┐
                                                              │
                                                              ▼
                                                    Back to PROCESSING


  DELETE FLOW:

   ┌────────┐
   │ ACTIVE │
   └────┬───┘
        │ soft_delete()
        ▼
   ┌──────────┐     restore()      ┌────────┐
   │ ARCHIVED │ ─────────────────► │ ACTIVE │
   └────┬─────┘                    └────────┘
        │
        │ hard_delete() (after retention period)
        ▼
   Permanently removed
   (file + chunks + vectors)
```

### 4.2. Upload Flow (Event-driven)

```
1. User uploads file
      │
      ▼
2. DocumentService.upload()
      ├── Save file to MinIO
      ├── Create Document record (status=PENDING)
      ├── Create DocumentVersion record
      └── Emit event: "document.created"
            │
            ▼
3. Event Handler (async)
      ├── Check KB settings (auto_process?)
      │     │
      │     ├── Yes → Emit "document.process_requested"
      │     │           │
      │     │           ▼
      │     │         Ingest Pipeline picks up
      │     │           │
      │     │           ├── Update status = PROCESSING
      │     │           ├── Parse → Chunk → Embed → Store
      │     │           ├── Update status = ACTIVE
      │     │           └── Emit "document.processed"
      │     │
      │     └── No → Stay PENDING (wait for manual trigger)
      │
      └── Update KB stats (document_count++)
```

### 4.3. Sync Flow

```
1. Trigger sync (manual/scheduled/webhook)
      │
      ▼
2. SyncService.trigger_sync()
      ├── Create SyncJob record (status=PENDING)
      └── Queue sync task
            │
            ▼
3. Sync Worker picks up job
      ├── Update job status = RUNNING
      ├── Get adapter for source_type
      ├── List files from source (with patterns)
      │
      │   For each file:
      │     ├── Check if exists (by remote_path)
      │     │     │
      │     │     ├── New file:
      │     │     │   ├── Download content
      │     │     │   ├── Create Document (status=PENDING)
      │     │     │   └── files_added++
      │     │     │
      │     │     ├── Existing, changed (by remote_modified_at or hash):
      │     │     │   ├── Download new content
      │     │     │   ├── Create new DocumentVersion
      │     │     │   ├── Update Document
      │     │     │   └── files_updated++
      │     │     │
      │     │     └── Existing, unchanged:
      │     │         └── files_skipped++
      │     │
      │     └── On error: files_failed++, log to error_details
      │
      ├── Handle deletions (files in DB but not in source)
      │   └── Mark as archived (soft delete)
      │
      ├── Update job: status=COMPLETED, stats
      └── Emit "sync.completed"
            │
            ▼
4. Event Handler
      └── Trigger processing for new/updated documents
```

### 4.4. Delete Flow

```
1. User deletes document
      │
      ▼
2. DocumentService.delete(soft=True)
      ├── Update status = ARCHIVED
      └── Emit event: "document.archived"
            │
            ▼
3. Event Handler
      ├── Mark chunks as inactive
      ├── Remove vectors from search (hoặc filter out)
      └── Update KB stats (document_count--)

4. Background Job (after retention period, e.g., 30 days)
      ├── Hard delete: remove file from MinIO
      ├── Delete chunks from DB
      ├── Delete vectors from vector store
      └── Emit "document.permanently_deleted"
```

---

## 5. Service Layer

### 5.1. KnowledgeBaseService

| Method                                     | Mô tả                              |
| ------------------------------------------ | ---------------------------------- |
| `create_kb(tenant_id, name, settings)`     | Tạo knowledge base mới             |
| `update_kb(kb_id, updates)`                | Cập nhật KB settings               |
| `delete_kb(kb_id)`                         | Xóa KB và cascade delete documents |
| `get_kb(kb_id)`                            | Lấy thông tin KB                   |
| `list_kbs(tenant_id, filters)`             | Danh sách KBs của tenant           |
| `get_stats(kb_id)`                         | Lấy stats (document/chunk/size)    |
| `bind_pipeline(kb_id, pipeline_config_id)` | Gắn pipeline config cho KB         |

### 5.2. DocumentService (Enhanced)

**Upload operations:**

| Method                         | Mô tả                           |
| ------------------------------ | ------------------------------- |
| `upload(file, kb_id, context)` | Upload document, trigger ingest |
| `upload_batch(files, kb_id)`   | Bulk upload                     |

**CRUD operations:**

| Method                              | Mô tả                             |
| ----------------------------------- | --------------------------------- |
| `get(doc_id, context)`              | Lấy document với permission check |
| `list(kb_id, filters, context)`     | Danh sách documents               |
| `update_metadata(doc_id, metadata)` | Cập nhật metadata                 |
| `delete(doc_id, soft=True)`         | Soft delete (archive)             |
| `delete_batch(doc_ids)`             | Bulk delete                       |
| `restore(doc_id)`                   | Restore document từ archived      |

**Download operation:**

| Method                           | Mô tả               |
| -------------------------------- | ------------------- |
| `download(doc_id, version=None)` | Stream file content |

**Versioning operations:**

| Method                                 | Mô tả                  |
| -------------------------------------- | ---------------------- |
| `upload_new_version(doc_id, file)`     | Upload version mới     |
| `list_versions(doc_id)`                | Danh sách versions     |
| `rollback_to_version(doc_id, version)` | Rollback về version cũ |

**Processing operations:**

| Method                          | Mô tả                     |
| ------------------------------- | ------------------------- |
| `trigger_processing(doc_id)`    | Manual trigger ingest     |
| `get_processing_status(doc_id)` | Lấy trạng thái processing |
| `retry_failed(doc_id)`          | Retry document failed     |

### 5.3. SyncService

**Config management:**

| Method                                           | Mô tả             |
| ------------------------------------------------ | ----------------- |
| `create_sync_config(kb_id, source_type, config)` | Tạo sync config   |
| `update_sync_config(config_id, updates)`         | Cập nhật config   |
| `delete_sync_config(config_id)`                  | Xóa config        |
| `list_sync_configs(kb_id)`                       | Danh sách configs |

**Sync operations:**

| Method                                  | Mô tả                 |
| --------------------------------------- | --------------------- |
| `trigger_sync(config_id, triggered_by)` | Trigger sync manually |
| `cancel_sync(job_id)`                   | Cancel sync đang chạy |

**Sync jobs:**

| Method                               | Mô tả             |
| ------------------------------------ | ----------------- |
| `get_sync_job(job_id)`               | Lấy thông tin job |
| `list_sync_jobs(config_id, filters)` | Danh sách jobs    |
| `get_sync_history(config_id)`        | Lịch sử sync      |

### 5.4. StorageService

| Method                        | Mô tả                 |
| ----------------------------- | --------------------- |
| `upload_file(content, path)`  | Upload file lên MinIO |
| `download_file(path)`         | Stream download file  |
| `delete_file(path)`           | Xóa file              |
| `file_exists(path)`           | Check file tồn tại    |
| `get_file_info(path)`         | Lấy metadata file     |
| `calculate_hash(content)`     | Tính SHA256 hash      |
| `get_tenant_usage(tenant_id)` | Tổng storage đã dùng  |

---

## 6. API Endpoints

### 6.1. Knowledge Bases

| Method | Endpoint                                | Mô tả     |
| ------ | --------------------------------------- | --------- |
| POST   | `/api/v1/knowledge-bases`               | Create KB |
| GET    | `/api/v1/knowledge-bases`               | List KBs  |
| GET    | `/api/v1/knowledge-bases/{kb_id}`       | Get KB    |
| PATCH  | `/api/v1/knowledge-bases/{kb_id}`       | Update KB |
| DELETE | `/api/v1/knowledge-bases/{kb_id}`       | Delete KB |
| GET    | `/api/v1/knowledge-bases/{kb_id}/stats` | Get stats |

### 6.2. Documents

| Method | Endpoint                                    | Mô tả       |
| ------ | ------------------------------------------- | ----------- |
| POST   | `/api/v1/kb/{kb_id}/documents/upload`       | Upload      |
| POST   | `/api/v1/kb/{kb_id}/documents/upload-batch` | Bulk upload |
| GET    | `/api/v1/kb/{kb_id}/documents`              | List docs   |
| GET    | `/api/v1/documents/{doc_id}`                | Get doc     |
| PATCH  | `/api/v1/documents/{doc_id}`                | Update meta |
| DELETE | `/api/v1/documents/{doc_id}`                | Soft delete |
| POST   | `/api/v1/documents/{doc_id}/restore`        | Restore     |
| GET    | `/api/v1/documents/{doc_id}/download`       | Download    |

### 6.3. Document Versions

| Method | Endpoint                                  | Mô tả         |
| ------ | ----------------------------------------- | ------------- |
| POST   | `/api/v1/documents/{doc_id}/versions`     | New version   |
| GET    | `/api/v1/documents/{doc_id}/versions`     | List versions |
| GET    | `/api/v1/documents/{doc_id}/versions/{v}` | Get version   |
| POST   | `/api/v1/documents/{doc_id}/rollback/{v}` | Rollback      |

### 6.4. Document Processing

| Method | Endpoint                             | Mô tả        |
| ------ | ------------------------------------ | ------------ |
| POST   | `/api/v1/documents/{doc_id}/process` | Trigger proc |
| GET    | `/api/v1/documents/{doc_id}/status`  | Get status   |
| POST   | `/api/v1/documents/{doc_id}/retry`   | Retry failed |

### 6.5. Sync Configs

| Method | Endpoint                           | Mô tả         |
| ------ | ---------------------------------- | ------------- |
| POST   | `/api/v1/kb/{kb_id}/sync-configs`  | Create config |
| GET    | `/api/v1/kb/{kb_id}/sync-configs`  | List configs  |
| GET    | `/api/v1/sync-configs/{config_id}` | Get config    |
| PATCH  | `/api/v1/sync-configs/{config_id}` | Update        |
| DELETE | `/api/v1/sync-configs/{config_id}` | Delete        |

### 6.6. Sync Jobs

| Method | Endpoint                                   | Mô tả        |
| ------ | ------------------------------------------ | ------------ |
| POST   | `/api/v1/sync-configs/{config_id}/trigger` | Trigger sync |
| GET    | `/api/v1/sync-configs/{config_id}/jobs`    | List jobs    |
| GET    | `/api/v1/sync-jobs/{job_id}`               | Get job      |
| POST   | `/api/v1/sync-jobs/{job_id}/cancel`        | Cancel job   |

---

## 7. Code Structure

```
rag/
├── __init__.py
│
├── models/                          # SQLAlchemy models
│   ├── __init__.py
│   ├── knowledge_base.py            # NEW
│   ├── document.py                  # ENHANCED
│   ├── document_version.py          # NEW
│   ├── document_permission.py       # EXISTS
│   ├── sync_config.py               # NEW
│   └── sync_job.py                  # NEW
│
├── services/                        # Business logic
│   ├── __init__.py
│   ├── kb_service.py                # NEW - Knowledge base operations
│   ├── document_service.py          # ENHANCED - Full document lifecycle
│   ├── sync_service.py              # NEW - Sync management
│   └── storage_service.py           # NEW - MinIO wrapper enhanced
│
├── api/                             # FastAPI endpoints
│   ├── __init__.py
│   ├── knowledge_bases.py           # NEW
│   ├── documents.py                 # ENHANCED
│   ├── sync.py                      # NEW
│   └── deps.py                      # Dependencies (context, auth)
│
├── adapters/                        # External source adapters
│   ├── __init__.py
│   ├── base.py                      # EXISTS - BaseAdapter interface
│   ├── github.py                    # EXISTS - GitHub adapter
│   ├── confluence.py                # NEW (future)
│   └── s3.py                        # NEW (future)
│
├── events/                          # Event handling
│   ├── __init__.py
│   ├── document_events.py           # NEW - Event definitions
│   └── handlers.py                  # NEW - Event handlers
│
├── core/                            # Pipeline components
│   └── ... (existing pipeline core)
│
├── components/                      # Component implementations
│   └── ... (existing components)
│
└── pipelines/
    └── ... (existing pipelines)
```

---

## 8. Kế hoạch triển khai

### Phase 1A: Document Foundation (Tuần 1)

| Task                                             | Priority | Dependencies            |
| ------------------------------------------------ | -------- | ----------------------- |
| Knowledge Base model + basic CRUD                | P0       | None                    |
| Enhanced Document model (status, hash, metadata) | P0       | KB model                |
| Storage service (upload, download, delete)       | P0       | None                    |
| Basic document upload với status flow            | P0       | Document model, Storage |

**Deliverables:**

- Có thể tạo KB và upload documents
- Documents có status tracking
- Files được lưu trong MinIO với cấu trúc đúng

### Phase 1B: Integration với Pipeline (Tuần 2)

| Task                                         | Priority | Dependencies     |
| -------------------------------------------- | -------- | ---------------- |
| Document events (created, process_requested) | P0       | Document model   |
| Hook document upload → ingest pipeline       | P0       | Events, Pipeline |
| Update document status từ pipeline result    | P0       | Events           |
| Trigger processing API                       | P1       | All above        |

**Deliverables:**

- Upload document tự động trigger ingest
- Status được cập nhật: pending → processing → active/failed
- Có thể manual trigger processing

### Phase 1C: Sync Foundation (Tuần 3)

| Task                              | Priority | Dependencies |
| --------------------------------- | -------- | ------------ |
| SyncConfig model + CRUD           | P0       | KB model     |
| SyncJob model + tracking          | P0       | SyncConfig   |
| Manual sync trigger               | P0       | SyncJob      |
| GitHub adapter (enhance existing) | P1       | All above    |

**Deliverables:**

- Có thể cấu hình sync từ GitHub
- Manual trigger sync
- Track sync history và results

### Phase 2: Advanced Features (Tuần 4+)

| Task                           | Priority | Dependencies    |
| ------------------------------ | -------- | --------------- |
| Document versioning            | P1       | Phase 1         |
| Batch operations               | P1       | Phase 1         |
| Scheduled sync (cron)          | P2       | Phase 1C        |
| More adapters (Confluence, S3) | P2       | Phase 1C        |
| Quota management               | P2       | Storage service |
| Cleanup orphaned files         | P2       | Storage service |

---

## Phụ lục

### A. Tổng hợp thay đổi

| Category                 | Hiện tại         | Cần bổ sung                              |
| ------------------------ | ---------------- | ---------------------------------------- |
| **Knowledge Base**       | Chỉ là string ID | Full model với settings, stats           |
| **Document Status**      | Không có         | pending → processing → active → archived |
| **Document Version**     | Không có         | Track history, rollback                  |
| **Sync Config**          | Không có         | Persistent config, patterns, schedule    |
| **Sync Job**             | Không có         | Track execution, results, errors         |
| **Storage**              | Basic upload     | Download, delete, hash, usage tracking   |
| **Events**               | Không có         | Document lifecycle events                |
| **Pipeline Integration** | Không có         | Auto-trigger ingest on upload            |

### B. MinIO Path Convention

```
/{tenant_id}/
  /{kb_id}/
    /documents/
      /{doc_id}/
        /v{version}/
          {original_filename}
```

Example:

```
/tenant-abc123/kb-xyz789/documents/doc-456/v1/report.pdf
/tenant-abc123/kb-xyz789/documents/doc-456/v2/report.pdf
```

### C. Event Types

| Event                          | Trigger            | Handler Action                            |
| ------------------------------ | ------------------ | ----------------------------------------- |
| `document.created`             | After upload       | Update KB stats, maybe trigger processing |
| `document.process_requested`   | Manual or auto     | Queue for ingest pipeline                 |
| `document.processing`          | Pipeline started   | Update status                             |
| `document.processed`           | Pipeline completed | Update status, stats                      |
| `document.failed`              | Pipeline failed    | Update status, log error                  |
| `document.archived`            | Soft delete        | Mark chunks inactive, update stats        |
| `document.permanently_deleted` | Hard delete        | Remove all data                           |
| `sync.started`                 | Sync job begins    | Update job status                         |
| `sync.completed`               | Sync job done      | Trigger processing for new docs           |
| `sync.failed`                  | Sync job error     | Log error, update status                  |
