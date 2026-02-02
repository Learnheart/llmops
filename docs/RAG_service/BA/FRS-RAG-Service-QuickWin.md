# Functional Requirements Specification (FRS)
# RAG Service QuickWin

| Metadata | Value |
|----------|-------|
| **Document ID** | FRS-RAG-001 |
| **Version** | 1.0 |
| **Status** | Draft |
| **PRD Reference** | PRD-RAG-001 |
| **Owner** | Business Analyst |
| **Reviewers** | Product Owner, Tech Lead |
| **Last Updated** | 2026-02-02 |

---

## 1. Introduction

### 1.1 Purpose
Tài liệu này mô tả chi tiết các yêu cầu chức năng của RAG Service QuickWin MVP, bao gồm input/output, validation rules, error handling và acceptance criteria cho từng chức năng.

### 1.2 Scope
FRS cover các modules trong MVP scope:
- Module 1: Document Upload
- Module 2: Pipeline Configuration
- Module 3: Query Interface
- Module 4: Knowledge Base Management
- Module 5: Document Management
- Module 6: Trash Management
- Module 7: Authentication

### 1.3 Conventions

**Requirement ID Format**: `FR-[Module]-[Number]`
- FR = Functional Requirement
- Module = UP (Upload), PC (Pipeline Config), QI (Query Interface), KB (Knowledge Base), DM (Document Management), TR (Trash), AU (Auth)

**Priority Levels**:
- **P0**: Must have - MVP blocker
- **P1**: Should have - Important nhưng có thể delay
- **P2**: Nice to have - Future consideration

---

## 2. Module 1: Document Upload

### 2.1 Overview
Module cho phép user upload documents vào Knowledge Base để processing và indexing.

### 2.2 Functional Requirements

#### FR-UP-001: Single File Upload
| Attribute | Description |
|-----------|-------------|
| **Priority** | P0 |
| **Description** | User có thể upload một file vào Knowledge Base |
| **Actor** | Authenticated User với quyền write trên KB |

**Input**:
| Field | Type | Required | Validation |
|-------|------|----------|------------|
| file | Binary | Yes | Max 50MB, allowed extensions |
| knowledge_base_id | UUID | Yes | Valid KB, user có quyền |

**Allowed File Types**:
| Extension | MIME Type | Category |
|-----------|-----------|----------|
| .pdf | application/pdf | Document |
| .docx | application/vnd.openxmlformats-officedocument.wordprocessingml.document | Document |
| .doc | application/msword | Document |
| .xlsx | application/vnd.openxmlformats-officedocument.spreadsheetml.sheet | Spreadsheet |
| .xls | application/vnd.ms-excel | Spreadsheet |
| .txt | text/plain | Text |
| .md | text/markdown | Text |
| .png | image/png | Image |
| .jpg/.jpeg | image/jpeg | Image |
| .mp3 | audio/mpeg | Audio |
| .wav | audio/wav | Audio |
| .html | text/html | Web |

**Output** (Success - HTTP 202 Accepted):
```json
{
  "document_id": "uuid",
  "filename": "string",
  "status": "pending",
  "uploaded_at": "ISO8601 datetime",
  "size_bytes": number,
  "message": "Document queued for processing"
}
```

**Error Responses**:
| Error Code | HTTP Status | Condition | Message |
|------------|-------------|-----------|---------|
| ERR_UP_001 | 400 | File exceeds 50MB | "File size exceeds maximum limit of 50MB" |
| ERR_UP_002 | 400 | Unsupported file type | "File type '{ext}' is not supported" |
| ERR_UP_003 | 400 | Empty file | "Cannot upload empty file" |
| ERR_UP_004 | 404 | KB not found | "Knowledge Base not found" |
| ERR_UP_005 | 403 | No permission | "You don't have permission to upload to this Knowledge Base" |
| ERR_UP_006 | 409 | Duplicate filename | "A document with this name already exists. Choose: Replace, Keep Both, or Cancel" |
| ERR_UP_007 | 507 | Storage quota exceeded | "Storage quota exceeded for this Knowledge Base" |

**Acceptance Criteria**:
```gherkin
Given I am logged in and have write access to KB "HR Policies"
When I upload a valid PDF file "employee_handbook.pdf" (10MB)
Then I should see upload progress indicator
And I should receive confirmation with document_id
And document status should be "pending"
And I should see the document in the document list with "Processing" badge

Given I am logged in and have write access to KB "HR Policies"
When I upload a file larger than 50MB
Then I should see error "File size exceeds maximum limit of 50MB"
And no document should be created

Given I am logged in and have write access to KB "HR Policies"
When I upload a file "handbook.pdf" that already exists in the KB
Then I should see conflict dialog with options: "Replace", "Keep Both", "Cancel"
```

---

#### FR-UP-002: Batch File Upload
| Attribute | Description |
|-----------|-------------|
| **Priority** | P0 |
| **Description** | User có thể upload nhiều files cùng lúc |
| **Actor** | Authenticated User với quyền write trên KB |

**Input**:
| Field | Type | Required | Validation |
|-------|------|----------|------------|
| files | Binary[] | Yes | Max 20 files, max 50MB each |
| knowledge_base_id | UUID | Yes | Valid KB, user có quyền |

**Output** (Success - HTTP 202 Accepted):
```json
{
  "batch_id": "uuid",
  "total_files": 5,
  "successful": 4,
  "failed": 1,
  "documents": [
    {"document_id": "uuid", "filename": "file1.pdf", "status": "pending"},
    {"document_id": "uuid", "filename": "file2.docx", "status": "pending"},
    ...
  ],
  "errors": [
    {"filename": "invalid.exe", "error": "File type not supported"}
  ]
}
```

**Acceptance Criteria**:
```gherkin
Given I am logged in and have write access to KB "HR Policies"
When I drag and drop 5 valid PDF files into the upload area
Then I should see batch upload progress
And I should receive summary showing 5/5 successful
And all 5 documents should appear in document list with "Processing" badge

Given I am logged in and have write access to KB "HR Policies"
When I upload 5 files where 2 have unsupported extensions
Then I should see partial success: "3 uploaded, 2 failed"
And I should see error details for failed files
And 3 valid documents should be created
```

---

#### FR-UP-003: Upload Progress Tracking
| Attribute | Description |
|-----------|-------------|
| **Priority** | P1 |
| **Description** | User có thể xem tiến độ upload và processing |
| **Actor** | Authenticated User |

**States**:
| Status | Description | UI Indicator |
|--------|-------------|--------------|
| uploading | File đang được upload | Progress bar (%) |
| pending | File đã upload, chờ processing | Spinner + "Queued" |
| processing | Đang parse, chunk, embed | Spinner + "Processing" |
| ready | Hoàn thành, có thể query | Green checkmark |
| failed | Lỗi trong quá trình xử lý | Red X + error message |

**Acceptance Criteria**:
```gherkin
Given I have uploaded a document
When the document is being uploaded
Then I should see upload progress percentage

Given a document is queued for processing
When I view the document list
Then I should see status "Queued" with queue position (e.g., "3rd in queue")

Given a document is being processed
When I view the document list
Then I should see status "Processing" with estimated time remaining

Given a document processing fails
When I view the document list
Then I should see status "Failed" with clickable error message
And I should have option to "Retry" processing
```

---

#### FR-UP-004: Drag and Drop Upload
| Attribute | Description |
|-----------|-------------|
| **Priority** | P1 |
| **Description** | User có thể kéo thả files vào upload zone |
| **Actor** | Authenticated User |

**Acceptance Criteria**:
```gherkin
Given I am on the KB document list page
When I drag files over the upload zone
Then the zone should highlight to indicate drop target

Given I am on the KB document list page
When I drop valid files onto the upload zone
Then files should start uploading automatically

Given I am on the KB document list page
When I drop files including unsupported types
Then valid files should upload
And unsupported files should show error immediately
```

---

## 3. Module 2: Pipeline Configuration

### 3.1 Overview
Module cho phép user cấu hình pipeline xử lý documents thông qua giao diện No-Code.

### 3.2 Functional Requirements

#### FR-PC-001: View Pipeline Configuration
| Attribute | Description |
|-----------|-------------|
| **Priority** | P0 |
| **Description** | User có thể xem cấu hình pipeline hiện tại của KB |
| **Actor** | Authenticated User với quyền read trên KB |

**Output**:
```json
{
  "knowledge_base_id": "uuid",
  "pipeline_config": {
    "ingestion": {
      "chunking": {
        "strategy": "semantic",
        "chunk_size": 512,
        "overlap": 50
      },
      "embedding": {
        "model": "text-embedding-3-small",
        "dimension": 1536
      }
    },
    "retrieval": {
      "search": {
        "type": "hybrid",
        "vector_weight": 0.7,
        "keyword_weight": 0.3,
        "top_k": 10
      },
      "reranker": {
        "enabled": true,
        "model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
        "top_n": 5
      }
    },
    "generation": {
      "model": "gpt-4o-mini",
      "temperature": 0.3,
      "max_tokens": 1000,
      "system_prompt": "You are a helpful assistant..."
    }
  },
  "last_modified": "ISO8601 datetime",
  "modified_by": "user_id"
}
```

---

#### FR-PC-002: Edit Chunking Configuration
| Attribute | Description |
|-----------|-------------|
| **Priority** | P0 |
| **Description** | User có thể cấu hình chiến lược chunking |
| **Actor** | Authenticated User với quyền config trên KB |

**Configurable Options**:
| Option | Type | Values | Default | Description |
|--------|------|--------|---------|-------------|
| strategy | enum | fixed, semantic, paragraph, sentence | semantic | Chiến lược chia chunk |
| chunk_size | integer | 100-2000 | 512 | Kích thước chunk (tokens) |
| overlap | integer | 0-500 | 50 | Số tokens overlap giữa chunks |

**Constraints**:
- `overlap` phải < `chunk_size`
- Khi thay đổi chunking config, documents cần re-process

**Acceptance Criteria**:
```gherkin
Given I am on the Pipeline Configuration page
When I select chunking strategy "semantic"
And I set chunk_size to 512 and overlap to 50
And I click "Save Configuration"
Then configuration should be saved
And I should see confirmation message
And existing documents should be marked for re-processing

Given I am on the Pipeline Configuration page
When I set overlap value greater than chunk_size
Then I should see validation error "Overlap must be less than chunk size"
And Save button should be disabled
```

---

#### FR-PC-003: Edit Search Configuration
| Attribute | Description |
|-----------|-------------|
| **Priority** | P0 |
| **Description** | User có thể cấu hình search behavior |
| **Actor** | Authenticated User với quyền config trên KB |

**Configurable Options**:
| Option | Type | Values | Default | Description |
|--------|------|--------|---------|-------------|
| search_type | enum | vector, keyword, hybrid | hybrid | Loại search |
| vector_weight | float | 0.0-1.0 | 0.7 | Trọng số vector search (hybrid only) |
| keyword_weight | float | 0.0-1.0 | 0.3 | Trọng số keyword search (hybrid only) |
| top_k | integer | 1-50 | 10 | Số results từ search |

**Constraints**:
- `vector_weight + keyword_weight` phải = 1.0
- Khi thay đổi search config, không cần re-process documents

**UI Elements**:
- Slider cho vector/keyword weight (linked - thay đổi 1 cái tự động adjust cái kia)
- Dropdown cho search_type với visual explanation
- Number input cho top_k

---

#### FR-PC-004: Edit Reranker Configuration
| Attribute | Description |
|-----------|-------------|
| **Priority** | P1 |
| **Description** | User có thể enable/disable và cấu hình reranker |
| **Actor** | Authenticated User với quyền config trên KB |

**Configurable Options**:
| Option | Type | Values | Default | Description |
|--------|------|--------|---------|-------------|
| enabled | boolean | true/false | true | Bật/tắt reranker |
| model | enum | [list of models] | cross-encoder/ms-marco | Model reranker |
| top_n | integer | 1-20 | 5 | Số results sau rerank |

**Constraints**:
- `top_n` phải ≤ `top_k` của search config

---

#### FR-PC-005: Edit LLM Configuration
| Attribute | Description |
|-----------|-------------|
| **Priority** | P0 |
| **Description** | User có thể cấu hình LLM generation |
| **Actor** | Authenticated User với quyền config trên KB |

**Configurable Options**:
| Option | Type | Values | Default | Description |
|--------|------|--------|---------|-------------|
| model | enum | [available models] | gpt-4o-mini | LLM model |
| temperature | float | 0.0-2.0 | 0.3 | Creativity level |
| max_tokens | integer | 100-4000 | 1000 | Max response length |
| system_prompt | text | any | default prompt | Custom system prompt |

**Acceptance Criteria**:
```gherkin
Given I am on the Pipeline Configuration page
When I select LLM model "gpt-4o"
And I set temperature to 0.5
And I customize the system prompt
And I click "Save Configuration"
Then configuration should be saved
And next query should use new LLM settings
```

---

#### FR-PC-006: Reset to Defaults
| Attribute | Description |
|-----------|-------------|
| **Priority** | P1 |
| **Description** | User có thể reset configuration về default |
| **Actor** | Authenticated User với quyền config trên KB |

**Acceptance Criteria**:
```gherkin
Given I have modified pipeline configuration
When I click "Reset to Defaults"
Then I should see confirmation dialog
When I confirm
Then all settings should revert to system defaults
And documents should be marked for re-processing (if ingestion config changed)
```

---

#### FR-PC-007: Configuration Presets
| Attribute | Description |
|-----------|-------------|
| **Priority** | P2 |
| **Description** | User có thể chọn từ preset configurations |
| **Actor** | Authenticated User với quyền config trên KB |

**Available Presets**:
| Preset | Description | Use Case |
|--------|-------------|----------|
| Balanced | Default settings | General purpose |
| Precision | Higher accuracy, slower | Legal, compliance docs |
| Speed | Faster responses | High-volume queries |
| Conversational | Higher temperature | Chatbot-like interactions |

---

## 4. Module 3: Query Interface

### 4.1 Overview
Module cho phép user đặt câu hỏi và nhận câu trả lời từ KB.

### 4.2 Functional Requirements

#### FR-QI-001: Submit Query
| Attribute | Description |
|-----------|-------------|
| **Priority** | P0 |
| **Description** | User có thể gửi câu hỏi bằng ngôn ngữ tự nhiên |
| **Actor** | Authenticated User với quyền query trên KB |

**Input**:
| Field | Type | Required | Validation |
|-------|------|----------|------------|
| query | string | Yes | 1-2000 characters |
| knowledge_base_id | UUID | Yes | Valid KB với ít nhất 1 document ready |

**Output** (Success - HTTP 200):
```json
{
  "query_id": "uuid",
  "answer": "The employee handbook states that...",
  "sources": [
    {
      "document_id": "uuid",
      "document_name": "employee_handbook.pdf",
      "chunk_id": "uuid",
      "content_preview": "Section 3.2: Vacation policy...",
      "relevance_score": 0.95,
      "page_number": 12
    }
  ],
  "processing_time_ms": 1250,
  "model_used": "gpt-4o-mini"
}
```

**Error Responses**:
| Error Code | HTTP Status | Condition | Message |
|------------|-------------|-----------|---------|
| ERR_QI_001 | 400 | Empty query | "Please enter a question" |
| ERR_QI_002 | 400 | Query too long | "Question exceeds maximum length of 2000 characters" |
| ERR_QI_003 | 404 | KB not found | "Knowledge Base not found" |
| ERR_QI_004 | 400 | KB empty | "This Knowledge Base has no documents. Please upload documents first." |
| ERR_QI_005 | 400 | No ready documents | "Documents are still processing. Please wait." |
| ERR_QI_006 | 503 | LLM unavailable | "AI service temporarily unavailable. Please try again." |

**Acceptance Criteria**:
```gherkin
Given I am on the Query page of KB "HR Policies"
And the KB has at least 1 ready document
When I type "What is the vacation policy?"
And I press Enter or click Send
Then I should see loading indicator
And I should receive an answer within 5 seconds
And I should see source references below the answer

Given I am on the Query page of KB "HR Policies"
And the KB has no ready documents
When I try to submit a query
Then I should see message "Documents are still processing. Please wait."
And the input should be disabled
```

---

#### FR-QI-002: View Source References
| Attribute | Description |
|-----------|-------------|
| **Priority** | P0 |
| **Description** | User có thể xem sources được sử dụng để generate answer |
| **Actor** | Authenticated User |

**Display Requirements**:
- Mỗi source hiển thị: document name, content preview (50-100 chars), relevance score
- Sources được sort theo relevance_score (descending)
- Maximum 5 sources hiển thị initially, "Show more" để xem thêm

**Acceptance Criteria**:
```gherkin
Given I have received an answer to my query
When I look at the sources section
Then I should see list of source documents
And each source should show document name and preview
And sources should be ordered by relevance

Given I have received an answer with sources
When I click on a source
Then I should see expanded view with full chunk content
And I should see option to "Open Original Document"
```

---

#### FR-QI-003: Feedback on Response
| Attribute | Description |
|-----------|-------------|
| **Priority** | P1 |
| **Description** | User có thể provide feedback về chất lượng response |
| **Actor** | Authenticated User |

**Input**:
| Field | Type | Required | Options |
|-------|------|----------|---------|
| rating | enum | Yes | helpful, not_helpful |
| feedback_text | string | No | Optional comment |

**Acceptance Criteria**:
```gherkin
Given I have received an answer to my query
When I click the thumbs up icon
Then the icon should be highlighted
And my feedback should be recorded

Given I have received an answer to my query
When I click the thumbs down icon
Then I should see optional text field "What went wrong?"
And I can submit additional feedback
```

---

#### FR-QI-004: Query History (Session)
| Attribute | Description |
|-----------|-------------|
| **Priority** | P1 |
| **Description** | User có thể xem lịch sử queries trong session |
| **Actor** | Authenticated User |

**Requirements**:
- Hiển thị conversation history trong session hiện tại
- Scroll up để xem previous queries
- Clear history button để start fresh

**Note**: Persistent history across sessions là Phase 2 feature.

---

#### FR-QI-005: No Results Handling
| Attribute | Description |
|-----------|-------------|
| **Priority** | P0 |
| **Description** | Hệ thống xử lý gracefully khi không tìm được kết quả |
| **Actor** | System |

**Scenarios**:
| Scenario | Response |
|----------|----------|
| No relevant chunks found | "I couldn't find relevant information in the knowledge base for your question." |
| Low confidence results | "I found some information but I'm not confident about the answer. Here's what I found: [sources]" |
| Query about unrelated topic | "This question appears to be outside the scope of this knowledge base." |

**Acceptance Criteria**:
```gherkin
Given I am on the Query page of KB "HR Policies"
When I ask about something not in the documents (e.g., "What is the weather?")
Then I should see message indicating no relevant information found
And I should NOT see hallucinated answer
```

---

## 5. Module 4: Knowledge Base Management

### 5.1 Overview
Module cho phép user quản lý Knowledge Bases (CRUD operations).

### 5.2 Functional Requirements

#### FR-KB-001: Create Knowledge Base
| Attribute | Description |
|-----------|-------------|
| **Priority** | P0 |
| **Description** | User có thể tạo Knowledge Base mới |
| **Actor** | Authenticated User |

**Input**:
| Field | Type | Required | Validation |
|-------|------|----------|------------|
| name | string | Yes | 3-100 chars, unique within tenant |
| description | string | No | Max 500 chars |

**Output** (Success - HTTP 201):
```json
{
  "knowledge_base_id": "uuid",
  "name": "HR Policies",
  "description": "Company policies and procedures",
  "created_at": "ISO8601 datetime",
  "created_by": "user_id",
  "pipeline_config": { /* default config */ },
  "document_count": 0,
  "status": "active"
}
```

**Acceptance Criteria**:
```gherkin
Given I am logged in
When I click "Create Knowledge Base"
And I enter name "HR Policies" and description "Company policies"
And I click "Create"
Then new KB should be created with default pipeline config
And I should be redirected to KB detail page
And I should see empty document list with upload prompt

Given I am logged in
When I try to create KB with name that already exists
Then I should see error "A Knowledge Base with this name already exists"
```

---

#### FR-KB-002: List Knowledge Bases
| Attribute | Description |
|-----------|-------------|
| **Priority** | P0 |
| **Description** | User có thể xem danh sách KB mình có quyền access |
| **Actor** | Authenticated User |

**Output**:
```json
{
  "knowledge_bases": [
    {
      "knowledge_base_id": "uuid",
      "name": "HR Policies",
      "description": "...",
      "document_count": 15,
      "ready_count": 12,
      "processing_count": 3,
      "last_activity": "ISO8601 datetime",
      "my_role": "owner"
    }
  ],
  "total": 5,
  "page": 1,
  "per_page": 20
}
```

**Display Requirements**:
- Card view hoặc list view (user preference)
- Show document count và processing status
- Sort by: last activity, name, created date
- Filter by: owned by me, shared with me

---

#### FR-KB-003: View Knowledge Base Details
| Attribute | Description |
|-----------|-------------|
| **Priority** | P0 |
| **Description** | User có thể xem chi tiết của một KB |
| **Actor** | Authenticated User với quyền read |

**Displayed Information**:
- Basic info (name, description, created date)
- Statistics (document count, total size, query count)
- Document list với status
- Pipeline configuration summary
- Activity log (recent actions)

---

#### FR-KB-004: Edit Knowledge Base
| Attribute | Description |
|-----------|-------------|
| **Priority** | P0 |
| **Description** | User có thể edit KB metadata |
| **Actor** | Authenticated User với quyền edit |

**Editable Fields**:
- name
- description

**Acceptance Criteria**:
```gherkin
Given I am owner of KB "HR Policies"
When I click Edit and change name to "HR Documentation"
And I click Save
Then KB name should be updated
And I should see confirmation message
```

---

#### FR-KB-005: Delete Knowledge Base
| Attribute | Description |
|-----------|-------------|
| **Priority** | P0 |
| **Description** | User có thể xóa KB |
| **Actor** | Authenticated User với quyền delete (owner only) |

**Behavior**:
- Soft delete: KB và documents moved to Trash
- 30-day retention trước khi permanent delete
- All associated data (vectors, metadata) retained until permanent delete

**Acceptance Criteria**:
```gherkin
Given I am owner of KB "HR Policies" with 10 documents
When I click Delete KB
Then I should see confirmation dialog warning about consequences
When I type KB name to confirm and click Delete
Then KB should be moved to Trash
And KB should no longer appear in KB list
And I should see success message with "Undo" option (within 30 seconds)

Given I am NOT owner of KB "HR Policies"
When I try to delete KB
Then I should see error "Only the owner can delete this Knowledge Base"
```

---

## 6. Module 5: Document Management

### 6.1 Overview
Module cho phép user quản lý documents trong KB.

### 6.2 Functional Requirements

#### FR-DM-001: List Documents
| Attribute | Description |
|-----------|-------------|
| **Priority** | P0 |
| **Description** | User có thể xem danh sách documents trong KB |
| **Actor** | Authenticated User với quyền read |

**Display Columns**:
| Column | Description |
|--------|-------------|
| Name | Filename với icon theo file type |
| Status | pending/processing/ready/failed |
| Size | Human-readable size (e.g., 2.5 MB) |
| Uploaded | Date + time |
| Uploaded By | User name |
| Actions | View, Delete |

**Features**:
- Search by filename
- Filter by status
- Sort by any column
- Pagination (default 20 per page)

---

#### FR-DM-002: View Document Details
| Attribute | Description |
|-----------|-------------|
| **Priority** | P1 |
| **Description** | User có thể xem chi tiết của document |
| **Actor** | Authenticated User với quyền read |

**Displayed Information**:
- Filename, file type, size
- Upload date, uploader
- Processing status và history
- Number of chunks created
- Preview (if supported)
- Download option

---

#### FR-DM-003: Delete Document
| Attribute | Description |
|-----------|-------------|
| **Priority** | P0 |
| **Description** | User có thể xóa document khỏi KB |
| **Actor** | Authenticated User với quyền delete |

**Behavior**:
- Soft delete: document moved to Trash
- Vectors và metadata retained until permanent delete
- Document không còn được sử dụng trong queries

**Acceptance Criteria**:
```gherkin
Given I am viewing document list of KB "HR Policies"
When I select document "old_policy.pdf" and click Delete
Then I should see confirmation dialog
When I confirm
Then document should be moved to Trash
And document should no longer appear in document list
And document should no longer be used in queries
```

---

#### FR-DM-004: Batch Delete Documents
| Attribute | Description |
|-----------|-------------|
| **Priority** | P1 |
| **Description** | User có thể xóa nhiều documents cùng lúc |
| **Actor** | Authenticated User với quyền delete |

**Acceptance Criteria**:
```gherkin
Given I am viewing document list with checkboxes
When I select 5 documents using checkboxes
And I click "Delete Selected"
Then I should see confirmation "Delete 5 documents?"
When I confirm
Then all 5 documents should be moved to Trash
```

---

#### FR-DM-005: Download Original Document
| Attribute | Description |
|-----------|-------------|
| **Priority** | P1 |
| **Description** | User có thể download file gốc |
| **Actor** | Authenticated User với quyền read |

---

#### FR-DM-006: Retry Failed Processing
| Attribute | Description |
|-----------|-------------|
| **Priority** | P1 |
| **Description** | User có thể retry processing cho failed documents |
| **Actor** | Authenticated User với quyền write |

**Acceptance Criteria**:
```gherkin
Given document "corrupted.pdf" has status "failed"
When I click "Retry" button
Then document status should change to "pending"
And document should be re-queued for processing
```

---

## 7. Module 6: Trash Management

### 7.1 Overview
Module quản lý items đã bị soft delete.

### 7.2 Functional Requirements

#### FR-TR-001: View Trash
| Attribute | Description |
|-----------|-------------|
| **Priority** | P1 |
| **Description** | User có thể xem items trong Trash |
| **Actor** | Authenticated User |

**Display**:
- Separate sections: Knowledge Bases, Documents
- Show deleted date và days remaining
- Show original location (parent KB for documents)

---

#### FR-TR-002: Restore from Trash
| Attribute | Description |
|-----------|-------------|
| **Priority** | P1 |
| **Description** | User có thể restore items từ Trash |
| **Actor** | Authenticated User (original deleter hoặc owner) |

**Acceptance Criteria**:
```gherkin
Given document "policy.pdf" is in Trash
When I click "Restore"
Then document should be restored to original KB
And document should appear in KB document list
And document should be available for queries again (if was ready)

Given KB "HR Policies" was deleted
When I restore it from Trash
Then KB and all its documents should be restored
```

---

#### FR-TR-003: Permanent Delete
| Attribute | Description |
|-----------|-------------|
| **Priority** | P1 |
| **Description** | User có thể permanently delete items |
| **Actor** | Authenticated User với quyền (owner only) |

**Acceptance Criteria**:
```gherkin
Given document "policy.pdf" is in Trash
When I click "Delete Permanently"
Then I should see warning "This action cannot be undone"
When I confirm
Then document and all associated data should be permanently deleted
```

---

#### FR-TR-004: Auto-Purge After 30 Days
| Attribute | Description |
|-----------|-------------|
| **Priority** | P1 |
| **Description** | System tự động permanent delete sau 30 ngày |
| **Actor** | System |

**Behavior**:
- Daily job check items older than 30 days
- Permanent delete và cleanup all associated data
- No notification (user was warned at delete time)

---

#### FR-TR-005: Empty Trash
| Attribute | Description |
|-----------|-------------|
| **Priority** | P2 |
| **Description** | User có thể empty toàn bộ Trash |
| **Actor** | Authenticated User (owner level) |

---

## 8. Module 7: Authentication

### 8.1 Overview
Module quản lý user authentication.

### 8.2 Functional Requirements

#### FR-AU-001: Login
| Attribute | Description |
|-----------|-------------|
| **Priority** | P0 |
| **Description** | User có thể login vào hệ thống |
| **Actor** | Any user |

**Input**:
| Field | Type | Required | Validation |
|-------|------|----------|------------|
| email | string | Yes | Valid email format |
| password | string | Yes | Non-empty |

**Error Responses**:
| Error Code | Condition | Message |
|------------|-----------|---------|
| ERR_AU_001 | Invalid credentials | "Invalid email or password" |
| ERR_AU_002 | Account locked | "Account locked. Contact administrator." |
| ERR_AU_003 | Account inactive | "Account is inactive. Contact administrator." |

**Security**:
- Rate limiting: 5 failed attempts → 15 minute lockout
- Session expires after 8 hours of inactivity
- JWT token với refresh mechanism

---

#### FR-AU-002: Logout
| Attribute | Description |
|-----------|-------------|
| **Priority** | P0 |
| **Description** | User có thể logout |
| **Actor** | Authenticated User |

**Behavior**:
- Clear session/token
- Redirect to login page
- All tabs logged out (optional: per-device logout)

---

#### FR-AU-003: Session Management
| Attribute | Description |
|-----------|-------------|
| **Priority** | P0 |
| **Description** | System quản lý user sessions |
| **Actor** | System |

**Requirements**:
- Token refresh để maintain session
- Logout on token expiry
- Show session timeout warning 5 minutes before expiry

---

#### FR-AU-004: Password Reset (Future)
| Attribute | Description |
|-----------|-------------|
| **Priority** | P2 |
| **Description** | User có thể reset password |
| **Note** | Deferred to Phase 2 |

---

## 9. Non-Functional Requirements Summary

| Category | Requirement | Target |
|----------|-------------|--------|
| **Performance** | Query response time | P95 < 5 seconds |
| **Performance** | Upload response time | < 500ms (async) |
| **Performance** | Page load time | < 2 seconds |
| **Availability** | System uptime | 99.5% |
| **Scalability** | Concurrent users | 100+ per tenant |
| **Security** | Data encryption | At rest and in transit |
| **Usability** | Setup without help | 90% users |

---

## 10. Traceability Matrix

| PRD Feature | FRS Requirements |
|-------------|------------------|
| F1: Document Upload | FR-UP-001 to FR-UP-004 |
| F2: Pipeline Configuration | FR-PC-001 to FR-PC-007 |
| F3: Query Interface | FR-QI-001 to FR-QI-005 |
| F4: Knowledge Base Management | FR-KB-001 to FR-KB-005 |
| F5: Document Management | FR-DM-001 to FR-DM-006 |
| F6: Basic Auth | FR-AU-001 to FR-AU-003 |
| F7: Processing Status | FR-UP-003 |
| F8: Trash Management | FR-TR-001 to FR-TR-005 |

---

## 11. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-02 | BA Team | Initial draft |
