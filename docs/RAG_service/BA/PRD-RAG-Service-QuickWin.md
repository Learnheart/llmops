# Product Requirements Document (PRD)
# RAG Service QuickWin

| Metadata | Value |
|----------|-------|
| **Document ID** | PRD-RAG-001 |
| **Version** | 1.0 |
| **Status** | Draft |
| **Owner** | Business Analyst |
| **Stakeholders** | Product Owner, Tech Lead, Development Team, QA Team |
| **Last Updated** | 2026-02-02 |

---

## 1. Executive Summary

### 1.1 Problem Statement

Các doanh nghiệp hiện đang gặp phải những thách thức lớn trong việc quản lý và khai thác tri thức nội bộ:

1. **Tìm kiếm thông tin mất nhiều thời gian**: Nhân viên phải tìm kiếm qua nhiều nguồn tài liệu khác nhau (SharePoint, Google Drive, wiki nội bộ, email) để tìm câu trả lời cho các câu hỏi nghiệp vụ.

2. **Thiếu công cụ self-service**: Mọi câu hỏi về policy, quy trình, sản phẩm đều phải hỏi trực tiếp những người có kinh nghiệm, tạo ra bottleneck và giảm năng suất làm việc.

3. **Khó khăn trong việc xây dựng hệ thống RAG**: Việc xây dựng hệ thống Q&A thông minh yêu cầu developer và kiến thức chuyên môn về AI/ML, khiến nhiều doanh nghiệp không thể tiếp cận công nghệ này.

### 1.2 Proposed Solution

**RAG Service QuickWin** là nền tảng No-Code RAG (Retrieval-Augmented Generation) cho phép người dùng không có nền tảng kỹ thuật có thể xây dựng và vận hành hệ thống hỏi đáp thông minh dựa trên tài liệu nội bộ, chỉ thông qua giao diện cấu hình trực quan.

### 1.3 Vision Statement

> *"Bất kỳ ai cũng có thể biến kho tài liệu của mình thành một assistant thông minh trong vài phút, không cần viết một dòng code nào."*

---

## 2. Target Users & Personas

### 2.1 Primary Personas

RAG Service QuickWin được thiết kế để phục vụ **tất cả các domain trong doanh nghiệp**. Dưới đây là các persona đại diện:

#### Persona 1: Knowledge Manager (Non-Technical)
| Attribute | Description |
|-----------|-------------|
| **Role** | HR Manager, Admin Lead, Training Coordinator |
| **Technical Skill** | Thấp - Sử dụng được các công cụ office cơ bản |
| **Goal** | Xây dựng KB cho policy, quy trình nội bộ để nhân viên tự tra cứu |
| **Current Workflow** | Upload docs lên SharePoint → Nhân viên hỏi trực tiếp → Trả lời manual |
| **Pain Points** | Mất thời gian trả lời câu hỏi lặp đi lặp lại, thông tin không nhất quán |
| **Success Criteria** | Tạo được KB hoạt động trong <15 phút mà không cần hỗ trợ IT |

#### Persona 2: Product Owner / Business Analyst
| Attribute | Description |
|-----------|-------------|
| **Role** | Product Manager, Business Analyst, Project Lead |
| **Technical Skill** | Trung bình - Hiểu concept kỹ thuật cơ bản |
| **Goal** | Xây dựng KB cho product documentation, FAQs, competitive intelligence |
| **Current Workflow** | Tổng hợp docs thủ công → Gửi cho team khi có câu hỏi |
| **Pain Points** | Thông tin phân tán, khó update, team thường hỏi lại những điều đã documented |
| **Success Criteria** | Team có thể tự tìm câu trả lời 80% câu hỏi thường gặp |

#### Persona 3: IT Administrator
| Attribute | Description |
|-----------|-------------|
| **Role** | System Admin, DevOps, IT Support Lead |
| **Technical Skill** | Cao - Có thể cấu hình hệ thống phức tạp |
| **Goal** | Deploy và quản lý platform cho toàn doanh nghiệp |
| **Current Workflow** | Manage multiple tools → Hỗ trợ các team tạo KB |
| **Pain Points** | Mỗi team yêu cầu tool khác nhau, khó quản lý tập trung |
| **Success Criteria** | Multi-tenant platform với RBAC, self-service cho các team |

### 2.2 User Segments by Domain

| Domain | Use Cases | Typical Documents |
|--------|-----------|-------------------|
| **HR / Admin** | Policy Q&A, Onboarding, Benefits info | Policies, handbooks, forms |
| **Customer Support** | FAQ bot, Ticket resolution | FAQs, product guides, troubleshooting |
| **Sales / Marketing** | Product info, Competitive analysis | Brochures, case studies, pricing |
| **Engineering** | Technical docs, Runbooks | API docs, architecture, procedures |
| **Legal / Compliance** | Contract review, Regulation lookup | Contracts, regulations, guidelines |
| **Finance** | Expense policies, Reporting guides | Policies, templates, procedures |

---

## 3. Goals & Success Metrics

### 3.1 Business Goals

| Goal | Description | Priority |
|------|-------------|----------|
| **G1** | Giảm thời gian tìm kiếm thông tin nội bộ | P0 |
| **G2** | Cho phép non-technical users tự xây dựng RAG system | P0 |
| **G3** | Cung cấp giải pháp self-hosted cho doanh nghiệp lo ngại data privacy | P1 |
| **G4** | Tạo nền tảng multi-tenant để nhiều team sử dụng chung | P1 |

### 3.2 Key Success Metrics (KPIs)

#### Primary Metric: Time-to-Value
| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Time to first working pipeline** | ≤ 15 phút | Từ lúc user đăng nhập đến khi pipeline trả lời câu hỏi đầu tiên |
| **Setup without IT support** | 90% users | Tỷ lệ user hoàn thành setup mà không cần escalate |

#### Secondary Metrics
| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Pipeline flexibility** | 100% config-driven | Mọi thay đổi behavior đều qua UI, không cần code |
| **User adoption** | +20% MoM | Số lượng active KBs và queries tăng trưởng |
| **Query satisfaction** | ≥ 80% helpful | User feedback (thumbs up/down) trên responses |
| **System availability** | 99.5% uptime | Uptime monitoring |

### 3.3 Non-Goals (Out of Scope for MVP)

- Tích hợp tự động với external sources (GitHub, Confluence, SharePoint) - *Future Phase*
- Advanced analytics và reporting dashboard - *Future Phase*
- Fine-tuning LLM models - *Không trong roadmap*
- Real-time collaborative editing - *Không trong roadmap*

---

## 4. Product Scope

### 4.1 MVP Scope (Phase 1) - Core RAG

MVP tập trung vào **core value proposition**: cho phép user upload documents, cấu hình pipeline, và query để nhận câu trả lời.

```
┌─────────────────────────────────────────────────────────────┐
│                     MVP SCOPE                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Upload    │───▶│   Config    │───▶│    Query    │     │
│  │  Documents  │    │  Pipeline   │    │  Interface  │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│         │                 │                   │             │
│         ▼                 ▼                   ▼             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │  Document   │    │  Knowledge  │    │   Response  │     │
│  │ Management  │    │    Base     │    │   + Source  │     │
│  │  (CRUD)     │    │   Config    │    │  References │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Basic Admin (User Auth)                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### MVP Features

| Feature | Description | Priority |
|---------|-------------|----------|
| **F1: Document Upload** | Upload files (PDF, Word, Excel, Images, Audio) | P0 |
| **F2: Pipeline Configuration** | No-code UI để cấu hình processing pipeline | P0 |
| **F3: Query Interface** | Chat interface để hỏi đáp với KB | P0 |
| **F4: Knowledge Base Management** | CRUD operations cho KB | P0 |
| **F5: Document Management** | View, delete, restore documents trong KB | P0 |
| **F6: Basic Auth** | Login, logout, session management | P0 |
| **F7: Processing Status** | Hiển thị trạng thái processing của documents | P1 |
| **F8: Trash Management** | Soft delete với 30-day retention | P1 |

### 4.2 Future Phases

#### Phase 2: Multi-Tenant & Admin
- Tenant management
- User management với RBAC đầy đủ
- KB-level và Document-level permissions
- Audit logging

#### Phase 3: Integrations
- Sync từ GitHub, Confluence, SharePoint
- Webhook notifications
- API access cho external systems

#### Phase 4: Advanced Features
- Semantic caching
- Query analytics
- Conversation history
- Custom prompt templates

---

## 5. User Workflows

### 5.1 Workflow: First-Time Setup

```
┌──────────────────────────────────────────────────────────────────┐
│                    FIRST-TIME USER JOURNEY                        │
└──────────────────────────────────────────────────────────────────┘

Step 1: Login
    User đăng nhập vào hệ thống
    ↓
Step 2: Create Knowledge Base
    User tạo KB mới với tên và mô tả
    → System tạo KB với default pipeline config
    ↓
Step 3: Upload Documents
    User upload một hoặc nhiều files
    → System hiển thị upload progress
    → System bắt đầu processing async
    ↓
Step 4: (Optional) Configure Pipeline
    User có thể giữ default hoặc customize:
    - Chunking strategy
    - Embedding model
    - Search settings
    ↓
Step 5: Wait for Processing
    User thấy status của từng document:
    - Pending → Processing → Ready / Failed
    ↓
Step 6: Start Querying
    Khi documents Ready, user có thể bắt đầu hỏi
    → System trả lời với source references
```

### 5.2 Workflow: Daily Usage

```
┌──────────────────────────────────────────────────────────────────┐
│                      DAILY USER WORKFLOW                          │
└──────────────────────────────────────────────────────────────────┘

User mở KB → Chọn Query interface
    ↓
User nhập câu hỏi bằng ngôn ngữ tự nhiên
    ↓
System trả về:
    - Answer: Câu trả lời được generate từ LLM
    - Sources: List documents/chunks được sử dụng
    - Confidence: (optional) Độ tin cậy
    ↓
User có thể:
    - Hỏi tiếp (follow-up)
    - Rate response (helpful / not helpful)
    - Click source để xem document gốc
```

---

## 6. Assumptions & Constraints

### 6.1 Assumptions

| ID | Assumption | Risk if Wrong |
|----|------------|---------------|
| A1 | User có sẵn documents để upload (không cần tạo content) | Cần hướng dẫn tạo content |
| A2 | Documents chủ yếu là text-based (PDF, Word) | Cần support thêm formats |
| A3 | User chấp nhận async processing (không real-time) | Cần optimize performance |
| A4 | Default pipeline config phù hợp 80% use cases | Cần nhiều customization |
| A5 | English và Vietnamese là ngôn ngữ chính | Cần multi-language support |

### 6.2 Constraints

| ID | Constraint | Impact |
|----|------------|--------|
| C1 | Self-hosted deployment only (MVP) | Không có cloud version |
| C2 | Single LLM provider per deployment | Không switch LLM on-the-fly |
| C3 | File size limit 50MB per document | Large files cần split |
| C4 | Max 10,000 documents per KB (MVP) | Enterprise cần sharding |

### 6.3 Dependencies

| ID | Dependency | Owner | Status |
|----|------------|-------|--------|
| D1 | LLM API access (OpenAI/Azure/Self-hosted) | Deployment team | Required |
| D2 | Infrastructure (K8s/Docker) | DevOps | Required |
| D3 | Storage (MinIO/S3) | DevOps | Required |
| D4 | Vector DB (Milvus) | DevOps | Required |

---

## 7. Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| User không hiểu cách configure pipeline | High | High | Sensible defaults + tooltips + guided wizard |
| LLM responses không accurate | Medium | High | Source citations + feedback mechanism |
| Large file processing chậm | Medium | Medium | Progress indicator + background processing |
| Multi-format support phức tạp | Medium | Medium | Phân phase: text formats trước, media sau |

---

## 8. Release Criteria

### 8.1 MVP Launch Criteria

| Category | Criteria | Verification |
|----------|----------|--------------|
| **Functionality** | All P0 features working | QA sign-off |
| **Performance** | Query response < 5s (P95) | Load testing |
| **Reliability** | No critical bugs | Bug triage |
| **Usability** | User completes setup without help | UAT with 5 users |
| **Security** | Auth working, no data leaks | Security review |
| **Documentation** | User guide available | Doc review |

### 8.2 Definition of Done (per Feature)

- [ ] Functional requirements implemented
- [ ] Unit tests written (>80% coverage)
- [ ] Integration tests passed
- [ ] UI/UX reviewed
- [ ] Error handling implemented
- [ ] Performance acceptable
- [ ] Security reviewed
- [ ] Documentation updated

---

## 9. Appendix

### 9.1 Glossary

| Term | Definition |
|------|------------|
| **RAG** | Retrieval-Augmented Generation - kỹ thuật kết hợp search với LLM |
| **Knowledge Base (KB)** | Một collection của documents với pipeline config riêng |
| **Pipeline** | Chuỗi các bước xử lý từ document đến response |
| **Chunk** | Một phần nhỏ của document sau khi được chia nhỏ |
| **Embedding** | Vector representation của text để search |
| **No-Code** | Không yêu cầu viết code để sử dụng |

### 9.2 Related Documents

| Document | Description |
|----------|-------------|
| [HLD - High Level Design](../SA/rag_highlevel.md) | Kiến trúc kỹ thuật tổng quan |
| [FRS - Functional Requirements](./FRS-RAG-Service-QuickWin.md) | Chi tiết yêu cầu chức năng |
| [User Stories](./UserStories-RAG-Service-QuickWin.md) | User stories và acceptance criteria |
| [Wireframes](./Wireframes-RAG-Service-QuickWin.md) | Mô tả giao diện người dùng |

---

## 10. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-02 | BA Team | Initial draft |
