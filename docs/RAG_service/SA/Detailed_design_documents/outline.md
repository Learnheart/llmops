# Detailed Design Documentation — Guideline & Overview

## RAG Service QuickWin

---

## 1. Giới thiệu

Tài liệu này đóng vai trò là **bản đồ tổng thể** cho toàn bộ bộ tài liệu Detailed Design của hệ thống RAG Service QuickWin. Mục đích của nó là giúp mọi thành viên trong dự án — từ developer, QA, BA, cho đến stakeholder — hiểu rõ cấu trúc tài liệu, biết nên đọc tài liệu nào cho vai trò của mình, và nắm được mối liên hệ giữa các tài liệu.

Bộ tài liệu Detailed Design được tổ chức thành **5 document**, mỗi document phục vụ một mục đích riêng biệt nhưng liên kết chặt chẽ với nhau. Cách phân chia này không dựa trên ranh giới từng service đơn lẻ, mà dựa trên **tầng logic** của hệ thống — phản ánh đúng bản chất kiến trúc Config-as-Pipeline, nơi mà pipeline config là trung tâm điều phối mọi hoạt động.

---

## 2. Nguyên tắc tổ chức tài liệu

### 2.1. Tại sao không chia theo từng service?

RAG Service QuickWin sử dụng kiến trúc **modular monolith with async task workers**, trong đó các processing component (Parser, Chunker, Embedder, Searcher...) không phải là service chạy độc lập với API và database riêng. Chúng là các **strategy module** được quản lý tập trung bằng factory pattern, được import và gọi trực tiếp bên trong worker process. Do đó, việc tách mỗi component thành một tài liệu riêng sẽ tạo ra nhiều tài liệu mỏng, thiếu ngữ cảnh, và buộc người đọc phải nhảy qua nhảy lại liên tục.

### 2.2. Nguyên tắc phân chia

Bộ tài liệu được chia theo 3 tiêu chí:

**Ranh giới deployment và runtime:** Những thành phần chạy cùng process, chia sẻ cùng lifecycle thì nằm chung tài liệu. API Server, Workers, và Data Layer là 3 ranh giới deployment rõ ràng nhất.

**Domain logic:** Những thành phần cùng giải quyết một bài toán nghiệp vụ thì nằm chung tài liệu. Ingestion và Retrieval là hai bài toán khác nhau về bản chất (batch write-heavy vs real-time read-heavy), nhưng chúng chia sẻ chung cơ chế orchestration (pipeline engine) và chung bộ component (Embedder dùng cho cả hai). Vì vậy, pipeline engine đứng riêng, còn các component được nhóm thành catalog.

**Audience:** Những nội dung phục vụ cùng nhóm người đọc thì nằm chung tài liệu. Data Governance phục vụ cả compliance team, security team, và developer — nên nó đứng riêng thay vì bị nhét vào một tài liệu kỹ thuật thuần túy.

### 2.3. Cấu trúc nhất quán cho mỗi component

Dù nằm trong tài liệu nào, mỗi component hoặc module đều được mô tả theo cùng một template để đảm bảo tính nhất quán:

| Section | Mô tả |
|---------|-------|
| **Purpose & Scope** | Component này làm gì, ranh giới trách nhiệm ở đâu |
| **Interface Definition** | Input/output contract — nhận gì, trả gì |
| **Internal Design** | Class/component diagram, thuật toán, logic xử lý |
| **Configuration** | Các tham số có thể cấu hình, giá trị mặc định, ràng buộc |
| **Error Handling** | Các loại lỗi có thể xảy ra và cách xử lý |
| **Dependencies** | Phụ thuộc vào component/service/library nào |
| **Sequence Diagrams** | Luồng xử lý cho các flow chính |

---

## 3. Danh sách tài liệu Detailed Design

### Tổng quan nhanh

| # | Document | Phạm vi | Câu hỏi trả lời |
|---|----------|---------|-----------------|
| 1 | Pipeline Engine & Orchestration | Config schema, pipeline builder, executor, orchestration | "Hệ thống quyết định chạy cái gì và theo thứ tự nào?" |
| 2 | Processing Components Catalog | Parser, Chunker, Embedder, Searcher, Reranker, LLM... | "Mỗi bước xử lý cụ thể hoạt động như thế nào?" |
| 3 | Platform Services | Management API, Upload Handler, Auth, Trash Management | "User tương tác với hệ thống như thế nào?" |
| 4 | Data Architecture & Infrastructure | Database schema, storage, caching, deployment, CI/CD | "Dữ liệu được lưu ở đâu và hạ tầng vận hành ra sao?" |
| 5 | Data Governance & Compliance | RBAC policy, Lineage, Lifecycle, PII, Audit Logging | "Dữ liệu được quản trị và bảo vệ theo quy tắc nào?" |

---

### 3.1. Document 1 — Pipeline Engine & Orchestration

**Mục đích:** Mô tả cơ chế hoạt động cốt lõi của hệ thống — cách một pipeline được sinh ra từ config và thực thi. Đây là tài liệu nền tảng nhất, nên được viết và review đầu tiên, vì nó định nghĩa "mental model" mà mọi developer cần nắm trước khi implement bất kỳ component nào.

**Phạm vi bao gồm:**

- **Pipeline Config Schema:** Cấu trúc JSON/object mô tả một pipeline — các field, validation rules, giá trị mặc định, ràng buộc giữa các field (ví dụ: nếu chọn chunker loại A thì embedding model phải thuộc nhóm B).
- **Pipeline Builder:** Logic đọc config và resolve từng step thành concrete implementation thông qua factory pattern. Mô tả cách đăng ký strategy mới vào factory.
- **Pipeline Executor:** Cách worker chạy tuần tự các step, truyền output của step trước thành input step sau, xử lý khi một step fail giữa chừng.
- **Ingestion Pipeline Definition:** Các step bắt buộc vs optional, thứ tự thực thi, constraint giữa các step.
- **Retrieval Pipeline Definition:** Tương tự cho luồng query.
- **Config Versioning:** Khi user thay đổi config cho KB đã có dữ liệu — re-index toàn bộ hay chỉ áp dụng cho document mới?
- **Config Validation:** Những combination hợp lệ, conflict detection trước khi build pipeline.

**Audience chính:** Tất cả developer (bắt buộc đọc), Tech Lead, Architect.

**Tham chiếu đến:** Document 2 (các component được pipeline gọi), Document 3 (cách user tạo/sửa pipeline config trên UI), Document 4 (cách config được lưu trong database).

---

### 3.2. Document 2 — Processing Components Catalog

**Mục đích:** Mô tả chi tiết từng "viên gạch" mà pipeline engine sử dụng để lắp ráp pipeline. Tài liệu này được tổ chức như một cuốn sổ tay tra cứu — developer không cần đọc từ đầu đến cuối, mà tra đúng component mình cần.

**Phạm vi bao gồm:**

- **Content Extraction Group:**
    - Parser Service — strategy cho từng loại file (PDF, DOCX, Excel, Image OCR, Audio Transcription, HTML), library sử dụng, limitations, error cases.
    - Content Router — logic detect content type, fallback strategy.

- **Content Processing Group:**
    - Chunker Service — 3 strategy (Unstructured, Structured, Code AST), thuật toán, configurable parameters, ví dụ input → output.
    - Query Processor — query rewrite, query expansion logic.

- **Embedding Group:**
    - Embedder Service — model options, dimension output, batching strategy (batch chunks vs single query), model switch handling. Lưu ý: component này xuất hiện ở cả Ingestion và Retrieval pipeline.

- **Search & Ranking Group:**
    - Searcher Service — hybrid search (Milvus vector + Elasticsearch BM25 + RRF combination), weight configuration, permission filtering integration.
    - Reranker Service — model options, khi nào nên dùng/skip, performance impact.

- **Generation Group:**
    - LLM Service — prompt template design, context window management, token budgeting, streaming response handling.

**Audience chính:** Developer phụ trách implement từng component, QA (để viết test cases cho từng component).

**Tham chiếu đến:** Document 1 (cách component được đăng ký vào factory và được pipeline gọi), Document 4 (schema của data mà component đọc/ghi), Document 5 (các constraint governance mà component phải tuân thủ, ví dụ PII filtering trong Searcher).

**Lưu ý về mở rộng:** Nếu một component trở nên quá phức tạp (ví dụ Searcher cần support thêm nhiều search strategy, hoặc LLM Service cần hỗ trợ multi-turn conversation), component đó có thể được tách thành tài liệu riêng. Catalog lúc đó sẽ giữ phần tóm tắt và trỏ sang tài liệu chi tiết.

---

### 3.3. Document 3 — Platform Services

**Mục đích:** Mô tả các service không nằm trong processing pipeline nhưng thiết yếu cho hoạt động của hệ thống — bao gồm quản lý người dùng, upload tài liệu, xác thực, và các tính năng quản trị.

**Phạm vi bao gồm:**

- **Management Service:** CRUD cho User, Group, Knowledge Base, Pipeline Config. API endpoint design, request/response schema, validation logic.
- **Document Upload Handler:** Validation (file type, size, format), conflict detection (trùng tên file trong cùng KB), upload to MinIO, metadata creation trong PostgreSQL, push job vào queue kèm pipeline config. Đây là "cửa vào" của ingestion pipeline nhưng bản thân nó không thuộc pipeline.
- **Authentication Implementation:** JWT generation/validation/refresh, session management với Redis, token revocation. Phần này implement authentication policy được định nghĩa trong Document 5.
- **Permission Enforcement Middleware:** Cách API middleware intercept request, kiểm tra quyền dựa trên RBAC model, trả 403 khi unauthorized. Phần này implement access control policy từ Document 5.
- **Trash Management:** Soft delete flow, 30-day retention, hard delete cron job, restore mechanism.
- **API Gateway Configuration:** Routing rules, rate limiting per tenant, SSL termination, request logging.

**Audience chính:** Developer phụ trách platform/admin features, Frontend developer (cần hiểu API contract).

**Tham chiếu đến:** Document 1 (cách upload handler đẩy job vào queue cho pipeline engine), Document 4 (database schema cho users, KBs, documents), Document 5 (RBAC policy và governance rules mà platform services phải enforce).

**Mối quan hệ đặc biệt với Document 5:** Document 3 implement các policy mà Document 5 định nghĩa. Tương tự mối quan hệ giữa luật và cơ quan thực thi — Document 5 nói "phải làm gì" (what & why), Document 3 nói "làm thế nào" (how). Khi đọc phần Permission Enforcement trong Document 3, developer cần tham chiếu Document 5 để hiểu tại sao permission model được thiết kế như vậy.

---

### 3.4. Document 4 — Data Architecture & Infrastructure

**Mục đích:** Mô tả chi tiết cách dữ liệu được lưu trữ, cách hạ tầng được triển khai, và cách hệ thống được vận hành. Đây là tài liệu reference chung cho tất cả developer và là tài liệu chính cho DevOps/DBA.

**Phạm vi bao gồm:**

- **Database Schema (PostgreSQL):** ERD đầy đủ với tất cả bảng, columns, indexes, constraints, JSONB fields, GIN indexes. Bao gồm schema cho: users, groups, tenants, knowledge_bases, documents, chunks, pipeline_configs, audit_logs, sessions.
- **Vector Store Schema (Milvus):** Collection schema, partition strategy (partition theo KB hay theo tenant), embedding dimensions, distance metric, scalar fields cho metadata filtering.
- **Search Index Schema (Elasticsearch):** Index mapping, analyzer configuration (đặc biệt cho tiếng Việt qua ICU plugin), field types, refresh interval.
- **Object Storage Design (MinIO):** Bucket structure, naming convention, lifecycle rules cho archive.
- **Caching Architecture (Redis):** Key naming convention, data structure cho từng loại cache (semantic cache, embedding cache, chunk cache, retrieval cache), TTL strategy, invalidation cascading khi document bị xóa hoặc re-index, memory estimation.
- **Pipeline Config Storage:** Cách lưu pipeline config trong PostgreSQL (JSONB blob vs normalized tables), indexing strategy cho phép query "tất cả KB đang dùng embedding model X".
- **Infrastructure & Deployment:** Docker Compose cho dev, Kubernetes manifests cho staging/production, resource allocation per component, networking, persistent volume configuration.
- **CI/CD Pipeline:** Branching strategy, build process, test stages, deployment stages, rollback procedure.
- **Monitoring Stack:** Prometheus + Grafana setup, Langfuse/Phoenix cho RAG tracing, alert rules, dashboard design.

**Audience chính:** DevOps, DBA, tất cả developer (tham khảo schema khi implement).

**Tham chiếu đến:** Document 1 (pipeline config storage schema phục vụ pipeline engine), Document 2 (schema cho data mà các component đọc/ghi), Document 3 (schema cho platform entities), Document 5 (audit log schema, data retention rules).

---

### 3.5. Document 5 — Data Governance & Compliance

**Mục đích:** Định nghĩa tất cả quy tắc quản trị và bảo vệ dữ liệu trong hệ thống. Đây là **single source of truth cho mọi governance policy** — khi bất kỳ ai hỏi "hệ thống xử lý dữ liệu cá nhân thế nào?" hoặc "ai được phép truy cập dữ liệu nào?", tài liệu này chứa câu trả lời.

Mỗi phần trong tài liệu này được tổ chức theo 3 tầng: **Policy** (chúng ta muốn đảm bảo điều gì), **Mechanism** (hệ thống implement điều đó như thế nào), và **Verification** (chúng ta kiểm chứng bằng cách nào).

**Phạm vi bao gồm:**

- **Access Control & RBAC:** Mô hình role-permission, ma trận phân quyền (role × action × resource), chính sách phân quyền ở 3 level (tenant, KB, document), quy tắc cấp/thu hồi quyền, enforcement ở tầng retrieval (cách kết hợp permission filter với search results). Trả lời câu hỏi: **"Ai được phép truy cập dữ liệu nào?"**

- **Data Lineage:** Cách hệ thống tracking nguồn gốc dữ liệu xuyên suốt pipeline — chunk tham chiếu về document gốc, embedding tham chiếu về chunk, câu trả lời liệt kê danh sách chunk đã sử dụng, pipeline config được lưu lại để truy xuất phương pháp tạo. Trả lời câu hỏi: **"Dữ liệu đến từ đâu và đi qua những bước nào?"**

- **Data Quality Control:** Validation đầu vào (text có ý nghĩa không, file có corrupt không), kiểm tra trùng lặp (hiện tại ở mức tên file), đánh dấu tài liệu lỗi thời. Trả lời câu hỏi: **"Dữ liệu có đáng tin cậy không?"**

- **Data Lifecycle Management:** 4 trạng thái (Pending, Active, Inactive, Error), state machine diagram, soft delete mechanism, 30-day retention trước hard delete, raw file giữ lại trên MinIO cho audit. Trả lời câu hỏi: **"Dữ liệu tồn tại bao lâu và qua những giai đoạn nào?"**

- **PII Detection & Masking:** Các loại PII cần detect (CMND, SĐT, email, số tài khoản), phương pháp detect (regex, NER), chính sách xử lý (mask, mã hóa, hoặc access-restricted), enforcement xuyên suốt pipeline (scan trước khi index, filter khi trả kết quả). Trả lời câu hỏi: **"Dữ liệu nhạy cảm được bảo vệ như thế nào?"**

- **Audit Logging:** Schema audit log, immutability guarantee (không ai được sửa/xóa audit log), retention policy (bao lâu), các events cần ghi (upload, delete, access, permission change, config change). Trả lời câu hỏi: **"Hệ thống chứng minh compliance bằng cách nào?"**

**Audience chính:** Compliance team, Security team, BA, Tech Lead, developer phụ trách governance features. Tài liệu này có thể được gửi cho khách hàng doanh nghiệp khi cần review.

**Tham chiếu đến:** Document 3 (implement enforcement cho access control, authentication), Document 1 (lineage tracking trong pipeline execution), Document 2 (PII detection tích hợp trong Searcher, Indexer), Document 4 (audit log schema, data retention configuration).

---

## 4. Mối liên hệ giữa các tài liệu

### 4.1. Sơ đồ quan hệ

```
                    ┌───────────────────────────┐
                    │    Document 5              │
                    │    Data Governance         │
                    │    & Compliance            │
                    │                            │
                    │    Defines policies for:   │
                    │    • Access Control (RBAC)  │
                    │    • Data Lineage          │
                    │    • Data Lifecycle         │
                    │    • PII Protection         │
                    │    • Audit Logging          │
                    └──────────┬────────────────┘
                               │ policies enforced by
                    ┌──────────▼────────────────┐
                    │    Document 3              │
                    │    Platform Services       │
                    │                            │
                    │    • Management API        │
                    │    • Upload Handler ──────────────┐ push job
                    │    • Auth Implementation   │      │ to queue
                    │    • Permission Middleware  │      │
                    └───────────────────────────┘      │
                                                        │
                    ┌───────────────────────────┐      │
                    │    Document 1              │◀─────┘
                    │    Pipeline Engine         │
                    │    & Orchestration         │
                    │                            │
                    │    • Config Schema         │
                    │    • Pipeline Builder      │
                    │    • Pipeline Executor ────────────┐ calls
                    │    • Ingestion Pipeline    │      │ components
                    │    • Retrieval Pipeline    │      │
                    └───────────────────────────┘      │
                                                        │
                    ┌───────────────────────────┐      │
                    │    Document 2              │◀─────┘
                    │    Processing Components   │
                    │    Catalog                 │
                    │                            │
                    │    • Parser, Chunker       │
                    │    • Embedder, Indexer ────────────┐ reads/writes
                    │    • Searcher, Reranker    │      │ data
                    │    • LLM Service           │      │
                    └───────────────────────────┘      │
                                                        │
                    ┌───────────────────────────┐      │
                    │    Document 4              │◀─────┘
                    │    Data Architecture       │
                    │    & Infrastructure        │
                    │                            │
                    │    • PostgreSQL Schema      │
                    │    • Milvus Schema          │
                    │    • ES Index Mapping       │
                    │    • MinIO, Redis           │
                    │    • Deployment, CI/CD      │
                    └───────────────────────────┘
```

### 4.2. Flow end-to-end qua các tài liệu

Để minh họa cách 5 tài liệu phối hợp với nhau, dưới đây là một luồng xử lý hoàn chỉnh — từ lúc user tạo KB đến lúc nhận được câu trả lời:

**Bước 1 — User tạo Knowledge Base và cấu hình pipeline trên UI:**
User chọn chunking strategy, embedding model, có bật reranker không, hybrid search weight... Hệ thống validate config và lưu vào PostgreSQL.
→ **Document 3** (Management API, Config UI → API flow)
→ **Document 1** (Config Schema definition, validation rules)
→ **Document 4** (Pipeline Config Storage schema)

**Bước 2 — User upload tài liệu:**
File được validate (type, size), kiểm tra conflict (trùng tên), upload lên MinIO, tạo metadata record trong PostgreSQL, đẩy job vào queue kèm pipeline config.
→ **Document 3** (Upload Handler)
→ **Document 5** (Data Quality Control policy, Access Control — user có quyền upload vào KB này không?)

**Bước 3 — Ingestion Worker xử lý tài liệu:**
Worker nhận job từ queue, đọc pipeline config, build pipeline từ factory, chạy tuần tự: Parse → Route → Chunk → Embed → Index.
→ **Document 1** (Pipeline Executor, Ingestion Pipeline definition)
→ **Document 2** (Chi tiết từng component: Parser, Content Router, Chunker, Embedder, Indexer)
→ **Document 5** (PII Detection trước khi index, Data Lineage tracking ở mỗi step)

**Bước 4 — User gửi câu hỏi:**
Query đi qua API, kiểm tra quyền, đẩy vào Retrieval Queue kèm pipeline config.
→ **Document 3** (API routing, Permission Middleware)
→ **Document 5** (Access Control — user được query KB nào, document nào?)

**Bước 5 — Retrieval Worker xử lý câu hỏi:**
Worker build retrieval pipeline từ config: Query Process → Embed → Search → Rerank → LLM Generate.
→ **Document 1** (Pipeline Executor, Retrieval Pipeline definition)
→ **Document 2** (Query Processor, Embedder, Searcher với hybrid search + permission filter, Reranker, LLM Service)
→ **Document 4** (Caching — semantic cache hit? Embedding cache hit?)
→ **Document 5** (Data Lineage — câu trả lời reference những chunk/document nào)

---

## 5. Hướng dẫn đọc theo vai trò

### 5.1. Developer mới join team

Bắt đầu bằng **Document 1** (Pipeline Engine) — đây là "bức tranh lớn" giúp bạn hiểu hệ thống hoạt động như thế nào ở mức tổng thể. Sau đó đọc **Document 2** (Components Catalog) cho component bạn được assign. Tra cứu **Document 4** (Data Architecture) khi cần biết schema của data mà component đọc/ghi.

### 5.2. Developer phụ trách Ingestion Pipeline

Đọc **Document 1** (phần Ingestion Pipeline definition), sau đó đọc **Document 2** (Parser, Content Router, Chunker, Embedder, Indexer). Tham khảo **Document 5** cho phần PII Detection và Data Lineage tracking cần tích hợp vào pipeline.

### 5.3. Developer phụ trách Retrieval/Query Engine

Đọc **Document 1** (phần Retrieval Pipeline definition), sau đó đọc **Document 2** (Query Processor, Embedder, Searcher, Reranker, LLM Service). Đặc biệt chú ý phần permission filtering trong Searcher — tham chiếu **Document 5** để hiểu RBAC enforcement ở tầng retrieval.

### 5.4. Developer phụ trách Platform/Admin

Đọc **Document 3** (Platform Services) là chính. Tham chiếu **Document 5** khi implement Authentication và Permission Middleware. Tra cứu **Document 4** cho schema của users, groups, KBs.

### 5.5. DevOps / DBA

Đọc **Document 4** (Data Architecture & Infrastructure) là chính. Tham khảo **Document 5** (phần Audit Logging retention, Data Lifecycle cho scheduled cleanup jobs).

### 5.6. QA / Tester

Đọc **Document 1** trước để hiểu config-as-pipeline pattern — điều này giúp thiết kế test cases cho config validation và pipeline composition. Sau đó đọc **Document 2** để viết test cases cho từng component. Đọc **Document 5** để viết test cases cho governance (permission enforcement, PII detection, audit logging).

### 5.7. BA / Product Owner

Đọc **Document 5** (Data Governance) và phần đầu của **Document 1** (Pipeline Config Schema) — đây là hai phần có nhiều business logic nhất. Document 5 cũng là tài liệu có thể chia sẻ với khách hàng hoặc compliance team.

### 5.8. Stakeholder / Management

Đọc file guideline này (tài liệu bạn đang đọc) để nắm tổng quan. Nếu cần đi sâu, đọc **Document 5** cho governance và compliance posture.

---

## 6. Quy ước chung

### 6.1. Versioning

Mỗi document sử dụng semantic versioning: `MAJOR.MINOR` (ví dụ: `1.0`, `1.1`, `2.0`). MAJOR tăng khi có thay đổi breaking (ví dụ: thay đổi pipeline config schema không backward-compatible). MINOR tăng khi bổ sung hoặc cập nhật nội dung không ảnh hưởng đến thiết kế tổng thể.

### 6.2. Changelog

Mỗi document có một bảng changelog ở đầu file, ghi lại ngày thay đổi, người thay đổi, và mô tả ngắn gọn nội dung thay đổi.

### 6.3. Cross-reference

Khi một document tham chiếu đến document khác, sử dụng format: `[Document X — Tên document, Section Y]`. Ví dụ: `[Document 1 — Pipeline Engine, Section 3.2: Config Validation]`.

### 6.4. Diagram

Tất cả diagram sử dụng công cụ thống nhất (Mermaid, PlantUML, hoặc draw.io) và được lưu trữ cùng với document source. Mỗi diagram phải có title và mô tả ngắn.

### 6.5. Review process

Mỗi document cần được review bởi ít nhất: 1 Tech Lead (cho tất cả documents), 1 developer từ team khác (cross-review), và 1 BA hoặc QA (cho Document 1, 3, 5).

---

## 7. Thứ tự viết được khuyến nghị

| Thứ tự | Document | Lý do ưu tiên |
|--------|----------|---------------|
| 1 | **Document 1: Pipeline Engine** | Nền tảng cho mọi thứ — developer cần hiểu mental model trước khi implement |
| 2 | **Document 5: Data Governance** | Các governance policy ảnh hưởng đến thiết kế của tất cả document khác |
| 3 | **Document 4: Data Architecture** | Database schema cần có trước khi developer bắt đầu code |
| 4 | **Document 2: Components Catalog** | Có thể viết song song khi developer implement từng component |
| 5 | **Document 3: Platform Services** | Có thể viết song song với Document 2 |

Document 2 và Document 3 có thể được viết song song bởi hai nhóm developer khác nhau, miễn là Document 1, 4, 5 đã sẵn sàng làm reference.

---

## Phụ lục: Danh sách file tài liệu

| File | Tên đầy đủ |
|------|-----------|
| `DD-01-pipeline-engine.md` | Detailed Design — Pipeline Engine & Orchestration |
| `DD-02-processing-components.md` | Detailed Design — Processing Components Catalog |
| `DD-03-platform-services.md` | Detailed Design — Platform Services |
| `DD-04-data-architecture.md` | Detailed Design — Data Architecture & Infrastructure |
| `DD-05-data-governance.md` | Detailed Design — Data Governance & Compliance |
| `DD-00-guideline.md` | Detailed Design — Guideline & Overview (tài liệu này) |