# Detailed Design — Platform Services

**Document ID:** DD-03
**Version:** 1.0
**Last Updated:** 2026-02-02
**Author:** Solution Architect Team

---

## Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-02 | SA Team | Initial version |

---

## Table of Contents

- [1. Overview](#1-overview)
- [2. Document Upload Handler](#2-document-upload-handler)
  - [2.1 Upload Flow](#21-upload-flow)
  - [2.2 Validation Rules](#22-validation-rules)
  - [2.3 Conflict Handling](#23-conflict-handling)
  - [2.4 API Endpoints](#24-api-endpoints)
- [3. Management Service](#3-management-service)
  - [3.1 User Management](#31-user-management)
  - [3.2 Group Management](#32-group-management)
  - [3.3 Knowledge Base Management](#33-knowledge-base-management)
  - [3.4 Pipeline Configuration](#34-pipeline-configuration)
- [4. Authentication Implementation](#4-authentication-implementation)
  - [4.1 JWT Token Flow](#41-jwt-token-flow)
  - [4.2 Session Management](#42-session-management)
  - [4.3 Token Refresh](#43-token-refresh)
- [5. Permission Enforcement Middleware](#5-permission-enforcement-middleware)
  - [5.1 Middleware Flow](#51-middleware-flow)
  - [5.2 Permission Checking](#52-permission-checking)
  - [5.3 Resource Guards](#53-resource-guards)
- [6. Trash Management](#6-trash-management)
  - [6.1 Soft Delete Flow](#61-soft-delete-flow)
  - [6.2 Restore Flow](#62-restore-flow)
  - [6.3 Auto Hard Delete](#63-auto-hard-delete)
- [7. API Gateway Configuration](#7-api-gateway-configuration)
  - [7.1 Routing Rules](#71-routing-rules)
  - [7.2 Rate Limiting](#72-rate-limiting)
  - [7.3 Request Logging](#73-request-logging)
- [8. Query Service](#8-query-service)
  - [8.1 Sync Query](#81-sync-query)
  - [8.2 Async Query](#82-async-query)
  - [8.3 Streaming Response](#83-streaming-response)
- [9. Dependencies](#9-dependencies)

---

## 1. Overview

### Purpose

Document này mô tả các platform services không nằm trong processing pipeline nhưng thiết yếu cho hoạt động của hệ thống. Bao gồm quản lý người dùng, upload tài liệu, xác thực, và các tính năng quản trị.

### Service Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         PLATFORM SERVICES                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                           API Gateway                                     │   │
│  │  • Routing     • Rate Limiting    • Auth Check    • Request Logging      │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                     │                                            │
│         ┌───────────────────────────┼───────────────────────────┐               │
│         ▼                           ▼                           ▼               │
│  ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐         │
│  │    Upload       │      │   Management    │      │    Query        │         │
│  │    Handler      │      │    Service      │      │    Service      │         │
│  │                 │      │                 │      │                 │         │
│  │ • Validate      │      │ • User CRUD     │      │ • Sync query    │         │
│  │ • Conflict      │      │ • Group CRUD    │      │ • Async query   │         │
│  │ • Store MinIO   │      │ • KB CRUD       │      │ • Job status    │         │
│  │ • Push Queue    │      │ • Pipeline cfg  │      │ • Streaming     │         │
│  └─────────────────┘      └─────────────────┘      └─────────────────┘         │
│         │                           │                           │               │
│         ▼                           ▼                           ▼               │
│  ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐         │
│  │    Trash        │      │ Authentication  │      │   Permission    │         │
│  │   Management    │      │    Service      │      │   Middleware    │         │
│  └─────────────────┘      └─────────────────┘      └─────────────────┘         │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Document Upload Handler

### Purpose & Scope

Document Upload Handler là "cửa vào" của ingestion pipeline, chịu trách nhiệm validate files, detect conflicts, lưu vào MinIO và push job vào queue.

### 2.1 Upload Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DOCUMENT UPLOAD FLOW                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  User Upload File(s)                                                            │
│         │                                                                        │
│         ▼                                                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                      UPLOAD HANDLER SERVICE                              │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│         │                                                                        │
│         ▼                                                                        │
│  ┌─────────────────┐                                                            │
│  │ 1. Auth Check   │── User đã login? Có quyền upload vào KB?                   │
│  └────────┬────────┘                                                            │
│           │ ✓                                                                    │
│           ▼                                                                      │
│  ┌─────────────────┐                                                            │
│  │ 2. Validation   │── File type, size, MIME type                               │
│  └────────┬────────┘                                                            │
│           │ ✓                                                                    │
│           ▼                                                                      │
│  ┌─────────────────┐                                                            │
│  │ 3. Generate ID  │── id = SHA256(kb_id + ":" + filename)[:16]                 │
│  └────────┬────────┘                                                            │
│           │                                                                      │
│           ▼                                                                      │
│  ┌─────────────────┐                                                            │
│  │ 4. Check Exist  │── SELECT * FROM uploaded_documents WHERE id = ?            │
│  └────────┬────────┘                                                            │
│           │                                                                      │
│      ┌────┴────────────────────┐                                                │
│      │                         │                                                │
│   Không tồn tại             Đã tồn tại                                          │
│      │                         │                                                │
│      │                    ┌────┴────┐                                           │
│      │                    │         │                                           │
│      │               is_active   is_active                                      │
│      │                = TRUE     = FALSE                                        │
│      │                    │         │                                           │
│      ▼                    ▼         ▼                                           │
│   CREATE              CONFLICT   REACTIVATE                                     │
│      │                    │         │                                           │
│      │              Return 409      │                                           │
│      │              with options    │                                           │
│      │                              │                                           │
│      ▼                              ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │ 5. Store to MinIO                                                        │    │
│  │    path = {tenant_id}/{kb_id}/documents/{doc_id}.{ext}                  │    │
│  └────────┬────────────────────────────────────────────────────────────────┘    │
│           │                                                                      │
│           ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │ 6. Save metadata to PostgreSQL                                           │    │
│  │    status = 'pending', is_active = TRUE                                  │    │
│  └────────┬────────────────────────────────────────────────────────────────┘    │
│           │                                                                      │
│           ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │ 7. Push to INGESTION QUEUE                                               │    │
│  │    { document_ids: [doc_id], kb_id, pipeline_config_id }                 │    │
│  └────────┬────────────────────────────────────────────────────────────────┘    │
│           │                                                                      │
│           ▼                                                                      │
│  Return 202 Accepted { job_id, document_id, status: "pending" }                 │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Validation Rules

```python
@dataclass
class UploadValidationConfig:
    # File type restrictions
    allowed_extensions: List[str] = field(default_factory=lambda: [
        'pdf', 'docx', 'doc', 'xlsx', 'xls', 'csv',
        'txt', 'md', 'html', 'htm',
        'png', 'jpg', 'jpeg', 'gif', 'webp',
        'mp3', 'wav', 'm4a', 'flac',
        'py', 'js', 'ts', 'java', 'go', 'rs'
    ])

    # Size limits
    max_file_size_mb: int = 100
    max_batch_size: int = 50
    max_total_size_mb: int = 500

    # Content validation
    validate_mime_type: bool = True
    scan_malware: bool = False  # Optional, requires ClamAV

class UploadValidator:
    def __init__(self, config: UploadValidationConfig):
        self.config = config

    def validate(self, file: UploadFile, kb_id: str) -> ValidationResult:
        errors = []

        # Check extension
        ext = file.filename.split('.')[-1].lower()
        if ext not in self.config.allowed_extensions:
            errors.append(f"File type '{ext}' not allowed")

        # Check size
        if file.size > self.config.max_file_size_mb * 1024 * 1024:
            errors.append(f"File size exceeds {self.config.max_file_size_mb}MB limit")

        # Check MIME type
        if self.config.validate_mime_type:
            detected_mime = magic.from_buffer(file.file.read(1024), mime=True)
            file.file.seek(0)
            if not self._mime_matches_extension(detected_mime, ext):
                errors.append(f"MIME type mismatch: {detected_mime}")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors
        )
```

### 2.3 Conflict Handling

| Case | Condition | Response | User Options |
|------|-----------|----------|--------------|
| **CREATE** | Document không tồn tại | 202 Accepted | - |
| **CONFLICT** | Document tồn tại, `is_active = TRUE` | 409 Conflict | SKIP, RENAME, REPLACE |
| **REACTIVATE** | Document tồn tại, `is_active = FALSE` | 202 Accepted (auto-replace) | - |

```python
class ConflictResolver:
    async def resolve(
        self,
        document_id: str,
        existing_doc: Document,
        resolution: ConflictResolution
    ) -> UploadResult:

        if resolution == ConflictResolution.SKIP:
            return UploadResult(
                status="skipped",
                message="Document already exists"
            )

        elif resolution == ConflictResolution.RENAME:
            # User must provide new filename
            raise ValueError("New filename required for RENAME resolution")

        elif resolution == ConflictResolution.REPLACE:
            # Delete old chunks from Milvus/ES
            await self._delete_old_chunks(existing_doc.id)

            # Upload new file to same path
            await self._upload_to_minio(new_file, existing_doc.minio_path)

            # Update metadata
            await self._update_document_metadata(existing_doc.id, new_file)

            # Push to queue for re-processing
            await self._push_to_queue(existing_doc.id)

            return UploadResult(
                status="replaced",
                document_id=existing_doc.id
            )
```

### 2.4 API Endpoints

```yaml
# Upload single file
POST /api/v1/knowledge-bases/{kb_id}/documents/upload
Content-Type: multipart/form-data
Body: file (binary)
Response: 202 Accepted
{
  "job_id": "job_001",
  "document_id": "abc123",
  "status": "pending",
  "message": "Document queued for processing"
}

# Upload multiple files
POST /api/v1/knowledge-bases/{kb_id}/documents/upload/batch
Content-Type: multipart/form-data
Body: files[] (multiple binaries)
Response: 202 Accepted
{
  "job_id": "job_002",
  "documents": [
    { "document_id": "abc123", "status": "pending" },
    { "document_id": "def456", "status": "pending" }
  ]
}

# Resolve conflict
POST /api/v1/knowledge-bases/{kb_id}/documents/upload/resolve
Content-Type: application/json
Body:
{
  "document_id": "abc123",
  "resolution": "replace",  // skip, rename, replace
  "new_filename": "report_v2.pdf"  // required for rename
}
Response: 202 Accepted

# Get upload status
GET /api/v1/jobs/{job_id}
Response: 200 OK
{
  "job_id": "job_001",
  "status": "processing",  // pending, processing, completed, error
  "progress": {
    "total": 5,
    "processed": 3,
    "failed": 0
  },
  "documents": [...]
}
```

---

## 3. Management Service

### 3.1 User Management

```yaml
# List users in tenant
GET /api/v1/users
Query: ?status=active&page=1&limit=20
Response: 200 OK
{
  "users": [...],
  "total": 100,
  "page": 1,
  "limit": 20
}

# Create user
POST /api/v1/users
Body:
{
  "email": "user@company.com",
  "full_name": "John Doe",
  "password": "...",
  "role_id": "kb_builder"
}
Response: 201 Created

# Update user
PATCH /api/v1/users/{user_id}
Body:
{
  "full_name": "John Updated",
  "status": "inactive"
}
Response: 200 OK

# Delete user (soft delete)
DELETE /api/v1/users/{user_id}
Response: 204 No Content

# Assign role to user
POST /api/v1/users/{user_id}/roles
Body:
{
  "role_id": "kb_builder",
  "scope_type": "kb",
  "scope_id": "kb_001"
}
Response: 201 Created
```

### 3.2 Group Management

```yaml
# List groups
GET /api/v1/groups
Response: 200 OK
{
  "groups": [
    {
      "id": "group_001",
      "name": "Finance Team",
      "member_count": 10
    }
  ]
}

# Create group
POST /api/v1/groups
Body:
{
  "name": "Finance Team",
  "description": "Finance department members"
}
Response: 201 Created

# Add members to group
POST /api/v1/groups/{group_id}/members
Body:
{
  "user_ids": ["user_001", "user_002"]
}
Response: 200 OK

# Remove member from group
DELETE /api/v1/groups/{group_id}/members/{user_id}
Response: 204 No Content
```

### 3.3 Knowledge Base Management

```yaml
# List KBs (user can access)
GET /api/v1/knowledge-bases
Response: 200 OK
{
  "knowledge_bases": [
    {
      "id": "kb_001",
      "name": "Company Policies",
      "document_count": 50,
      "permission_type": "custom",
      "my_permission": "builder"
    }
  ]
}

# Create KB
POST /api/v1/knowledge-bases
Body:
{
  "name": "Company Policies",
  "description": "Internal company policies and guidelines",
  "permission_type": "custom"
}
Response: 201 Created
{
  "id": "kb_001",
  "name": "Company Policies",
  "status": "active"
}

# Update KB
PATCH /api/v1/knowledge-bases/{kb_id}
Body:
{
  "name": "Updated Name",
  "permission_type": "public"
}
Response: 200 OK

# Delete KB
DELETE /api/v1/knowledge-bases/{kb_id}
Response: 204 No Content

# Grant access to KB
POST /api/v1/knowledge-bases/{kb_id}/access
Body:
{
  "entity_type": "user",  // or "group"
  "entity_id": "user_001",
  "permission_level": "viewer"  // viewer, contributor, builder
}
Response: 201 Created

# List KB access
GET /api/v1/knowledge-bases/{kb_id}/access
Response: 200 OK
{
  "access": [
    {
      "entity_type": "user",
      "entity_id": "user_001",
      "entity_name": "John Doe",
      "permission_level": "builder"
    },
    {
      "entity_type": "group",
      "entity_id": "group_001",
      "entity_name": "Finance Team",
      "permission_level": "viewer"
    }
  ]
}

# Revoke access
DELETE /api/v1/knowledge-bases/{kb_id}/access/{entity_type}/{entity_id}
Response: 204 No Content
```

### 3.4 Pipeline Configuration

```yaml
# Get KB pipelines
GET /api/v1/knowledge-bases/{kb_id}/pipelines
Response: 200 OK
{
  "ingestion_pipeline": {
    "id": "pipeline_001",
    "name": "Default Ingestion",
    "version": 1,
    "is_active": true,
    "config": {...}
  },
  "retrieval_pipeline": {
    "id": "pipeline_002",
    "name": "Hybrid Search",
    "version": 1,
    "is_active": true,
    "config": {...}
  }
}

# Create/Update pipeline
PUT /api/v1/knowledge-bases/{kb_id}/pipelines/ingestion
Body:
{
  "name": "Custom Ingestion",
  "config": {
    "parser": {...},
    "chunker": {...},
    "embedding": {...},
    "indexing": {...}
  }
}
Response: 200 OK
{
  "id": "pipeline_003",
  "version": 2,
  "requires_reindex": true,
  "message": "Embedding model changed. Re-indexing required."
}

# Trigger re-index
POST /api/v1/knowledge-bases/{kb_id}/reindex
Body:
{
  "pipeline_config_id": "pipeline_003"
}
Response: 202 Accepted
{
  "job_id": "reindex_001",
  "status": "pending",
  "total_documents": 50
}
```

---

## 4. Authentication Implementation

### 4.1 JWT Token Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           JWT AUTHENTICATION FLOW                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  LOGIN                                                                   │    │
│  │                                                                          │    │
│  │  POST /api/v1/auth/login                                                │    │
│  │  { email, password }                                                    │    │
│  │                                                                          │    │
│  │       │                                                                  │    │
│  │       ▼                                                                  │    │
│  │  1. Verify credentials against PostgreSQL                               │    │
│  │  2. Generate JWT access token (expires: 15min)                          │    │
│  │  3. Generate refresh token (expires: 7 days)                            │    │
│  │  4. Store session in Redis                                              │    │
│  │  5. Return tokens                                                       │    │
│  │                                                                          │    │
│  │  Response:                                                               │    │
│  │  {                                                                       │    │
│  │    "access_token": "eyJ...",                                            │    │
│  │    "refresh_token": "eyJ...",                                           │    │
│  │    "token_type": "Bearer",                                              │    │
│  │    "expires_in": 900                                                    │    │
│  │  }                                                                       │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  ACCESS TOKEN PAYLOAD                                                    │    │
│  │                                                                          │    │
│  │  {                                                                       │    │
│  │    "sub": "user_id",                                                    │    │
│  │    "tenant_id": "tenant_001",                                           │    │
│  │    "email": "user@company.com",                                         │    │
│  │    "roles": ["kb_builder"],                                             │    │
│  │    "groups": ["group_001", "group_002"],                                │    │
│  │    "session_id": "session_001",                                         │    │
│  │    "iat": 1706841600,                                                   │    │
│  │    "exp": 1706842500                                                    │    │
│  │  }                                                                       │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Session Management

```python
class SessionManager:
    def __init__(self, redis_client, session_ttl: int = 86400 * 7):
        self.redis = redis_client
        self.ttl = session_ttl

    async def create_session(self, user: User) -> Session:
        session_id = str(uuid.uuid4())
        token_hash = self._hash_token(secrets.token_urlsafe(32))

        session_data = {
            "user_id": str(user.id),
            "tenant_id": str(user.tenant_id),
            "email": user.email,
            "roles": user.roles,
            "groups": [str(g.id) for g in user.groups],
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat()
        }

        # Store in Redis
        await self.redis.hset(f"session:{session_id}", mapping=session_data)
        await self.redis.expire(f"session:{session_id}", self.ttl)

        # Store in PostgreSQL for audit
        await self._save_session_to_db(session_id, user, token_hash)

        return Session(
            id=session_id,
            user=user,
            token_hash=token_hash
        )

    async def get_session(self, session_id: str) -> Optional[SessionData]:
        data = await self.redis.hgetall(f"session:{session_id}")
        if not data:
            return None

        # Update last activity
        await self.redis.hset(
            f"session:{session_id}",
            "last_activity",
            datetime.utcnow().isoformat()
        )

        return SessionData(**data)

    async def revoke_session(self, session_id: str):
        await self.redis.delete(f"session:{session_id}")
        await self._update_session_db(session_id, revoked=True)
```

### 4.3 Token Refresh

```python
class TokenRefresher:
    async def refresh(self, refresh_token: str) -> TokenPair:
        # Verify refresh token
        try:
            payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise AuthError("Refresh token expired")
        except jwt.InvalidTokenError:
            raise AuthError("Invalid refresh token")

        # Check session still valid
        session = await self.session_manager.get_session(payload["session_id"])
        if not session:
            raise AuthError("Session expired or revoked")

        # Get fresh user data
        user = await self.user_repo.get_by_id(payload["sub"])
        if not user or user.status != "active":
            raise AuthError("User not found or inactive")

        # Generate new tokens
        access_token = self._generate_access_token(user, session.id)
        new_refresh_token = self._generate_refresh_token(user, session.id)

        return TokenPair(
            access_token=access_token,
            refresh_token=new_refresh_token
        )
```

---

## 5. Permission Enforcement Middleware

### 5.1 Middleware Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      PERMISSION MIDDLEWARE FLOW                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Incoming Request                                                                │
│       │                                                                          │
│       ▼                                                                          │
│  ┌─────────────────┐                                                            │
│  │ Extract Token   │── Authorization: Bearer {token}                            │
│  └────────┬────────┘                                                            │
│           │                                                                      │
│           ▼                                                                      │
│  ┌─────────────────┐                                                            │
│  │ Verify JWT      │── Signature, expiration, claims                            │
│  └────────┬────────┘                                                            │
│           │                                                                      │
│       ┌───┴───┐                                                                  │
│       │       │                                                                  │
│    Invalid   Valid                                                              │
│       │       │                                                                  │
│       ▼       ▼                                                                  │
│   401 Unauthorized                                                              │
│               │                                                                  │
│               ▼                                                                  │
│  ┌─────────────────┐                                                            │
│  │ Check Session   │── Session still valid in Redis?                            │
│  └────────┬────────┘                                                            │
│           │                                                                      │
│       ┌───┴───┐                                                                  │
│       │       │                                                                  │
│   Revoked   Active                                                              │
│       │       │                                                                  │
│       ▼       ▼                                                                  │
│   401 Unauthorized                                                              │
│               │                                                                  │
│               ▼                                                                  │
│  ┌─────────────────┐                                                            │
│  │ Build User      │── Create UserContext from token claims                     │
│  │ Context         │                                                            │
│  └────────┬────────┘                                                            │
│           │                                                                      │
│           ▼                                                                      │
│  ┌─────────────────┐                                                            │
│  │ Check Resource  │── User has permission for this resource?                   │
│  │ Permission      │                                                            │
│  └────────┬────────┘                                                            │
│           │                                                                      │
│       ┌───┴───┐                                                                  │
│       │       │                                                                  │
│   Denied   Allowed                                                              │
│       │       │                                                                  │
│       ▼       ▼                                                                  │
│   403 Forbidden    │                                                            │
│               │                                                                  │
│               ▼                                                                  │
│         Continue to Handler                                                     │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Permission Checking

```python
class PermissionChecker:
    def __init__(self, db_session):
        self.db = db_session

    async def check_kb_permission(
        self,
        user: UserContext,
        kb_id: str,
        required_level: str  # viewer, contributor, builder
    ) -> bool:
        """Check if user has required permission level for KB."""

        kb = await self.db.get(KnowledgeBase, kb_id)
        if not kb:
            return False

        # Check tenant isolation
        if kb.tenant_id != user.tenant_id:
            return False

        # Admin always has access
        if "admin" in user.roles or "tenant_admin" in user.roles:
            return True

        # KB owner has full access
        if kb.owner_id == user.id:
            return True

        # Check KB permission type
        if kb.permission_type == "public":
            return True
        elif kb.permission_type == "private":
            return kb.owner_id == user.id
        elif kb.permission_type == "custom":
            return await self._check_custom_access(user, kb_id, required_level)

        return False

    async def _check_custom_access(
        self,
        user: UserContext,
        kb_id: str,
        required_level: str
    ) -> bool:
        """Check kb_access table for custom permissions."""

        # Check user direct access
        user_access = await self.db.execute(
            select(KBAccess).where(
                KBAccess.kb_id == kb_id,
                KBAccess.entity_type == "user",
                KBAccess.entity_id == user.id
            )
        )
        user_access = user_access.scalar_one_or_none()

        if user_access:
            return self._level_sufficient(user_access.permission_level, required_level)

        # Check group access
        for group_id in user.group_ids:
            group_access = await self.db.execute(
                select(KBAccess).where(
                    KBAccess.kb_id == kb_id,
                    KBAccess.entity_type == "group",
                    KBAccess.entity_id == group_id
                )
            )
            group_access = group_access.scalar_one_or_none()
            if group_access and self._level_sufficient(
                group_access.permission_level, required_level
            ):
                return True

        return False

    def _level_sufficient(self, has_level: str, needs_level: str) -> bool:
        """Check if has_level >= needs_level."""
        levels = {"viewer": 1, "contributor": 2, "builder": 3}
        return levels.get(has_level, 0) >= levels.get(needs_level, 0)
```

### 5.3 Resource Guards

```python
# Decorator for protecting endpoints
def require_kb_permission(level: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, kb_id: str, user: UserContext, **kwargs):
            checker = PermissionChecker(get_db())
            has_permission = await checker.check_kb_permission(user, kb_id, level)

            if not has_permission:
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient permission. Required: {level}"
                )

            return await func(*args, kb_id=kb_id, user=user, **kwargs)
        return wrapper
    return decorator

# Usage
@router.post("/knowledge-bases/{kb_id}/documents/upload")
@require_kb_permission("contributor")
async def upload_document(
    kb_id: str,
    file: UploadFile,
    user: UserContext = Depends(get_current_user)
):
    # User has at least contributor access
    pass

@router.delete("/knowledge-bases/{kb_id}")
@require_kb_permission("builder")
async def delete_kb(
    kb_id: str,
    user: UserContext = Depends(get_current_user)
):
    # User has builder access (can delete KB)
    pass
```

---

## 6. Trash Management

### 6.1 Soft Delete Flow

```python
class TrashManager:
    async def soft_delete(self, document_id: str, user: UserContext) -> None:
        """Soft delete document - move to trash."""

        # Get document
        doc = await self.doc_repo.get_by_id(document_id)
        if not doc:
            raise NotFoundError("Document not found")

        # Check permission (owner or KB builder)
        if doc.owner_id != user.id:
            has_builder = await self.permission_checker.check_kb_permission(
                user, doc.kb_id, "builder"
            )
            if not has_builder:
                raise ForbiddenError("Cannot delete this document")

        # Soft delete document
        await self.doc_repo.update(document_id, {
            "is_active": False,
            "deleted_at": datetime.utcnow(),
            "deleted_by": user.id
        })

        # Soft delete chunks
        await self.chunk_repo.update_many(
            {"document_id": document_id},
            {"is_active": False}
        )

        # Note: Vectors in Milvus/ES are NOT deleted yet
        # They are filtered out at query time via is_active filter

        # Invalidate caches
        await self.cache_invalidator.invalidate_kb(doc.kb_id)

        # Audit log
        await self.audit_logger.log(
            event_type="DOCUMENT_DELETED",
            actor_id=user.id,
            target_type="document",
            target_id=document_id,
            metadata={"kb_id": str(doc.kb_id)}
        )
```

### 6.2 Restore Flow

```python
async def restore(self, document_id: str, user: UserContext) -> None:
    """Restore document from trash."""

    doc = await self.doc_repo.get_by_id(document_id)
    if not doc:
        raise NotFoundError("Document not found")

    if doc.is_active:
        raise BadRequestError("Document is not in trash")

    # Check permission
    if doc.owner_id != user.id:
        has_builder = await self.permission_checker.check_kb_permission(
            user, doc.kb_id, "builder"
        )
        if not has_builder:
            raise ForbiddenError("Cannot restore this document")

    # Check for conflict (same filename now exists)
    existing = await self.doc_repo.find_by_filename(doc.kb_id, doc.filename)
    if existing and existing.id != document_id and existing.is_active:
        raise ConflictError(
            "A document with this filename now exists",
            resolution_options=["rename", "replace"]
        )

    # Restore document
    await self.doc_repo.update(document_id, {
        "is_active": True,
        "deleted_at": None,
        "deleted_by": None
    })

    # Restore chunks
    await self.chunk_repo.update_many(
        {"document_id": document_id},
        {"is_active": True}
    )

    # Note: Vectors are still in Milvus/ES, just filtered back in

    # Audit log
    await self.audit_logger.log(
        event_type="DOCUMENT_RESTORED",
        actor_id=user.id,
        target_type="document",
        target_id=document_id
    )
```

### 6.3 Auto Hard Delete

```python
class HardDeleteJob:
    """Cron job to permanently delete old trashed documents."""

    def __init__(self, retention_days: int = 30):
        self.retention_days = retention_days

    async def run(self):
        """Run daily at 2:00 AM."""

        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)

        # Find documents to hard delete
        expired_docs = await self.doc_repo.find_many({
            "is_active": False,
            "deleted_at": {"$lt": cutoff_date}
        })

        for doc in expired_docs:
            await self._hard_delete(doc)

    async def _hard_delete(self, doc: Document):
        """Permanently delete document and all associated data."""

        try:
            # 1. Delete vectors from Milvus
            await self.milvus_client.delete(
                collection_name=f"kb_{doc.kb_id}",
                expr=f"document_id == '{doc.id}'"
            )

            # 2. Delete from Elasticsearch
            await self.es_client.delete_by_query(
                index=f"kb_{doc.kb_id}",
                body={"query": {"term": {"document_id": doc.id}}}
            )

            # 3. Delete chunks from PostgreSQL
            await self.chunk_repo.delete_many({"document_id": doc.id})

            # 4. Archive file to cold storage (optional)
            if self.config.archive_before_delete:
                await self._archive_to_cold_storage(doc)

            # 5. Delete file from MinIO
            await self.minio_client.remove_object(
                bucket_name="rag-storage",
                object_name=doc.minio_path
            )

            # 6. Delete document metadata
            await self.doc_repo.delete(doc.id)

            # 7. Audit log
            await self.audit_logger.log(
                event_type="DOCUMENT_HARD_DELETED",
                actor_type="system",
                actor_id=None,
                target_type="document",
                target_id=str(doc.id),
                metadata={
                    "filename": doc.filename,
                    "deleted_at": doc.deleted_at.isoformat(),
                    "retention_days": self.retention_days
                }
            )

        except Exception as e:
            logger.error(f"Failed to hard delete document {doc.id}: {e}")
            # Don't raise - continue with other documents
```

**Trash API Endpoints:**

```yaml
# List trash items
GET /api/v1/knowledge-bases/{kb_id}/trash
Response: 200 OK
{
  "documents": [
    {
      "id": "doc_001",
      "filename": "old_report.pdf",
      "deleted_at": "2026-01-01T10:00:00Z",
      "deleted_by": "user_001",
      "expires_at": "2026-01-31T10:00:00Z"  // auto hard delete date
    }
  ]
}

# Restore document
POST /api/v1/knowledge-bases/{kb_id}/trash/restore
Body:
{
  "document_ids": ["doc_001", "doc_002"]
}
Response: 200 OK
{
  "restored": ["doc_001"],
  "conflicts": [
    {
      "document_id": "doc_002",
      "reason": "filename_conflict",
      "existing_document_id": "doc_003"
    }
  ]
}

# Permanently delete (skip trash)
DELETE /api/v1/documents/{document_id}?permanent=true
Response: 204 No Content
```

---

## 7. API Gateway Configuration

### 7.1 Routing Rules

```yaml
# NGINX / Traefik configuration
routes:
  # API routes
  - path: /api/v1/auth/*
    service: auth-service
    rateLimit: 10/minute  # Strict for auth

  - path: /api/v1/knowledge-bases/*/documents/upload
    service: upload-handler
    maxBodySize: 100MB
    timeout: 300s

  - path: /api/v1/knowledge-bases/*/query
    service: query-service
    timeout: 60s

  - path: /api/v1/*
    service: management-service
    timeout: 30s

  # Health checks
  - path: /health
    service: all
    auth: false

  # Metrics (internal only)
  - path: /metrics
    service: prometheus
    internal: true
```

### 7.2 Rate Limiting

```python
class RateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def check_rate_limit(
        self,
        tenant_id: str,
        endpoint: str,
        limit: int,
        window_seconds: int = 60
    ) -> RateLimitResult:
        key = f"ratelimit:{tenant_id}:{endpoint}"
        now = time.time()

        # Use sorted set with timestamp scores
        pipe = self.redis.pipeline()

        # Remove old entries
        pipe.zremrangebyscore(key, 0, now - window_seconds)

        # Count current entries
        pipe.zcard(key)

        # Add current request
        pipe.zadd(key, {str(now): now})

        # Set expiry
        pipe.expire(key, window_seconds)

        _, count, _, _ = await pipe.execute()

        if count >= limit:
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_at=int(now + window_seconds)
            )

        return RateLimitResult(
            allowed=True,
            remaining=limit - count - 1,
            reset_at=int(now + window_seconds)
        )

# Rate limit configuration per tenant tier
RATE_LIMITS = {
    "free": {
        "upload": {"limit": 10, "window": 3600},      # 10/hour
        "query": {"limit": 100, "window": 3600},      # 100/hour
        "default": {"limit": 1000, "window": 3600}    # 1000/hour
    },
    "pro": {
        "upload": {"limit": 100, "window": 3600},
        "query": {"limit": 1000, "window": 3600},
        "default": {"limit": 10000, "window": 3600}
    },
    "enterprise": {
        "upload": {"limit": 1000, "window": 3600},
        "query": {"limit": 10000, "window": 3600},
        "default": {"limit": 100000, "window": 3600}
    }
}
```

### 7.3 Request Logging

```python
class RequestLogger:
    async def log_request(
        self,
        request: Request,
        response: Response,
        duration_ms: int
    ):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request.headers.get("X-Request-ID"),
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "user_id": getattr(request.state, "user_id", None),
            "tenant_id": getattr(request.state, "tenant_id", None),
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "ip_address": request.client.host,
            "user_agent": request.headers.get("User-Agent")
        }

        # Log to structured logging
        logger.info("request_completed", extra=log_entry)

        # For audit endpoints, also log to audit table
        if self._is_audit_endpoint(request.url.path):
            await self.audit_logger.log_request(log_entry)
```

---

## 8. Query Service

### 8.1 Sync Query

```yaml
POST /api/v1/knowledge-bases/{kb_id}/query
Content-Type: application/json
Body:
{
  "query": "What is the company vacation policy?",
  "options": {
    "top_k": 5,
    "include_sources": true
  }
}

Response: 200 OK
{
  "query_id": "query_001",
  "answer": "The company provides 15 days of paid vacation per year...",
  "sources": [
    {
      "chunk_id": "chunk_001",
      "document_id": "doc_001",
      "document_name": "HR_Policies.pdf",
      "excerpt": "...employees are entitled to 15 days...",
      "page": 12,
      "relevance_score": 0.92
    }
  ],
  "metadata": {
    "model": "gpt-4",
    "tokens_used": 1523,
    "latency_ms": 2150
  }
}
```

### 8.2 Async Query

```yaml
# Submit async query
POST /api/v1/knowledge-bases/{kb_id}/query/async
Body:
{
  "query": "What is the company vacation policy?"
}

Response: 202 Accepted
{
  "job_id": "query_job_001",
  "status": "pending",
  "estimated_wait_seconds": 5
}

# Check job status
GET /api/v1/jobs/{job_id}
Response: 200 OK
{
  "job_id": "query_job_001",
  "status": "completed",  // pending, processing, completed, error
  "result": {
    "answer": "...",
    "sources": [...]
  }
}
```

### 8.3 Streaming Response

```python
@router.post("/knowledge-bases/{kb_id}/query/stream")
async def stream_query(
    kb_id: str,
    request: QueryRequest,
    user: UserContext = Depends(get_current_user)
):
    """Stream query response token by token."""

    async def generate():
        # Get context chunks
        chunks = await retrieval_pipeline.retrieve(
            query=request.query,
            kb_id=kb_id,
            user=user
        )

        # Stream LLM response
        async for token in llm_service.generate_stream(
            query=request.query,
            context=chunks,
            config=request.llm_config
        ):
            yield f"data: {json.dumps({'token': token})}\n\n"

        # Send final metadata
        yield f"data: {json.dumps({'done': True, 'sources': [c.id for c in chunks]})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )
```

**Client-side consumption:**

```javascript
const response = await fetch('/api/v1/knowledge-bases/kb_001/query/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: 'What is...' })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      if (data.token) {
        appendToAnswer(data.token);
      } else if (data.done) {
        showSources(data.sources);
      }
    }
  }
}
```

---

## 9. Dependencies

### Service Dependencies

| Service | Depends On | Purpose |
|---------|-----------|---------|
| Upload Handler | MinIO, PostgreSQL, Redis Queue | Store files, metadata, queue jobs |
| Management Service | PostgreSQL | CRUD operations |
| Auth Service | PostgreSQL, Redis | User auth, session management |
| Permission Middleware | Redis (session), PostgreSQL (RBAC) | Enforce permissions |
| Query Service | Redis Queue, Retrieval Pipeline | Handle queries |
| Trash Manager | PostgreSQL, MinIO, Milvus, ES | Lifecycle management |

### Cross-Document References

| Reference | Document | Section |
|-----------|----------|---------|
| Pipeline integration | [DD-01-pipeline-engine.md] | Section 7: Queue Architecture |
| Processing components | [DD-02-processing-components.md] | All sections |
| Database schema | [DD-04-data-architecture.md] | Section 2: PostgreSQL Schema |
| RBAC policy | [DD-05-data-governance.md] | Section 1: Access Control |
| Audit logging | [DD-05-data-governance.md] | Section 6: Audit Logging |

---

*Document Version: 1.0*
*Last Updated: 2026-02-02*
