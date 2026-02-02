# High-Level System Architecture — RAG Service QuickWin

---

## Table of Contents

- [1. Executive Summary](#1-executive-summary)
  - [Design Principles](#design-principles)
  - [Key Features](#key-features)
- [2. Architecture Overview](#2-architecture-overview)
  - [Architectural Style](#architectural-style-microservices--monolith--event-driven--hybrid)
  - [High-level Architecture Diagram](#high-level-architecture-diagram)
  - [Danh sách các thành phần chính](#danh-sách-các-thành-phần-chính-và-trách-nhiệm)
- [3. Technology Stack](#3-technology-stack)
- [4. Data Architecture](#4-data-architecture)
  - [Domain Model Overview](#domain-model-overview)
  - [Chiến lược lưu trữ](#chiến-lược-lưu-trữ)
  - [Data Flow](#data-flow)
- [5. Integration & Communication](#5-integration--communication)
  - [Giao tiếp nội bộ](#giao-tiếp-nội-bộ)
  - [Message Queue Architecture](#message-queue-architecture)
  - [Tích hợp hệ thống bên ngoài](#tích-hợp-hệ-thống-bên-ngoài-cho-nguồn-đầu-vào-future-plan)
- [6. Infrastructure & Deployment](#6-infrastructure--deployment)
  - [Deployment Architecture (On-Premise)](#deployment-architecture-on-premise)
  - [Container Orchestration](#container-orchestration)
  - [Environments](#environments)
- [7. Security](#7-security)
  - [Authentication & Authorization](#authentication--authorization)
  - [Data Protection](#data-protection)
  - [Security Controls](#security-controls)
- [8. Non-Functional Requirements](#8-non-functional-requirements)
  - [Performance Targets](#performance-targets)
  - [Scalability Strategy](#scalability-strategy)
  - [Availability & Disaster Recovery](#availability--disaster-recovery)
  - [Monitoring & Alerting](#monitoring--alerting)
- [9. Risks & Trade-offs](#9-risks--trade-offs)
  - [Kiến trúc Trade-offs](#kiến-trúc-trade-offs-đã-chấp-nhận)
  - [Rủi ro chính](#rủi-ro-chính-và-giảm-thiểu)
  - [Technical Debt](#technical-debt-đã-biết)

---

## 1. Executive Summary
- Mục tiêu và phạm vi hệ thống
RAG Service QuickWin là một **No-Code RAG Platform** cho phép người dùng doanh nghiệp - đặc biệt là những người **không có background kỹ thuật** - có thể tự xây dựng và vận hành một hệ thống RAG hoàn chỉnh chỉ thông qua giao diện cấu hình trực quan.

### Design Principles

| Principle | Description |
|-----------|-------------|
| **No-Code First** | Người dùng non-technical có thể tự build pipeline |
| **Simplicity** | Config tối th



ểu, auto-detect khi có thể |
| **Multi data types processing** | Cho phép tạo dynamic pipeline để adapt với nhiều loại data |

### Key Features

| Feature | Description |
|---------|-------------|
| **No-Code Pipeline Builder** | Xây dựng RAG pipeline chỉ bằng UI config, không cần viết code |
| **RBAC** | Role-Based Access Control đầy đủ (Admin, Tenant Admin, KB Manager, Contributor, Viewer) |
| **Multi-Type Support** | Hỗ trợ PDF, Excel, Word, Image, Audio, HTML - tự động detect và parse |
| **Hybrid Search** | Vector (Milvus) + Fulltext (Elasticsearch) với weight tuỳ chỉnh |
| **Document Management** | Upload với conflict handling, soft delete, restore từ Trash |
| **Fine-grained Permissions** | Phân quyền ở mức Document và Knowledge Base |

---
## 2. Architecture Overview
### Architectural style (microservices / monolith / event-driven / hybrid…)**
- Kiến trúc chính sẽ sử dụng microservice để đảm bảo các service được phát triển độc lập và dễ đàng cho horizontal scale
- Các service (embedding, chunking, indexing, reranking, prompt optimiztion) sẽ được quản lý tập trung bằng factory strategies đơn giản. Quản lý dưới dạng dictionaries:
```
FACTORY = {
    ParserType.PRESENTATION.value: presentation,
    ParserType.PICTURE.value: picture,
    ParserType.AUDIO.value: audio,
    ParserType.EMAIL.value: email
}
```
### High-level architecture diagram
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           RAG SERVICE QUICKWIN                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                            User Interface                                 │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │   │
│  │  │   Upload     │  │  Configure   │  │    Query     │  │    Trash     │  │   │
│  │  │  Documents   │  │  Pipelines   │  │   Interface  │  │   Manager    │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                     │                                            │
│                                     ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                           API Gateway                                     │   │
│  │                    (Auth, Rate Limit, Routing)                            │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                     │                                            │
│         ┌───────────────────────────┼───────────────────────────┐               │
│         ▼                           ▼                           ▼               │
│  ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐         │
│  │    Upload       │      │    Push to      │      │   Management    │         │
│  │   Middleware    │      │     Queue       │      │    Service      │         │
│  │                 │      │                 │      │                 │         │
│  │ • Validate      │      │                 │      │ • User/Group    │         │
│  │ • Check conflict│      │                 │      │ • KB CRUD       │         │
│  │ • Store MinIO   │      │                 │      │ • Pipeline cfg  │         │
│  │                 │      │                 │      │ • Permissions   │         │
│  └────────┬────────┘      └────────┬────────┘      └─────────────────┘         │
│           │                        │                                             │
│           ▼                        ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                      Message Queue (Redis)                                │   │
│  │                                                                           │   │
│  │  ┌────────────────────────────┐    ┌────────────────────────────┐        │   │
│  │  │     Ingestion Queue        │    │     Retrieval Queue        │        │   │
│  │  │                            │    │                            │        │   │
│  │  │  Request contains:         │    │  Request contains:         │        │   │
│  │  │  • document_ids            │    │  • query                   │        │   │
│  │  │  • pipeline_config         │    │  • pipeline_config         │        │   │
│  │  │  • kb_id                   │    │  • kb_id                   │        │   │
│  │  │  • user_context            │    │  • user_context            │        │   │
│  │  └────────────────────────────┘    └────────────────────────────┘        │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│           │                                    │                                │
│           ▼                                    ▼                                │
│  ┌───────────────────────────────┐   ┌───────────────────────────────┐         │
│  │      Ingestion Worker         │   │      Retrieval Worker         │         │
│  │      (Auto-scale)             │   │      (Auto-scale)             │         │
│  │                               │   │                               │         │
│  │  ┌─────────────────────────┐  │   │  ┌─────────────────────────┐  │         │
│  │  │ 1. Parser Service       │  │   │  │ 1. Query Processor      │  │         │
│  │  │    (Extract content)    │  │   │  │    (Optiona l)          │  │         │
│  │  └───────────┬─────────────┘  │   │  └───────────┬─────────────┘  │         │
│  │              ▼                │   │              ▼                │         │
│  │  ┌─────────────────────────┐  │   │  ┌─────────────────────────┐  │         │
│  │  │ 2. Content Router       │  │   │  │ 2. Embedder Service     │  │         │
│  │  │    (Detect content type)│  │   │  │    (Query vector)       │  │         │
│  │  └─────┬───────┬───────┬───┘  │   │  └───────────┬─────────────┘  │         │
│  │        │       │       │      │   │              ▼                │         │
│  │        ▼       ▼       ▼      │   │  ┌─────────────────────────┐  │         │
│  │  ┌─────────────────────────┐  │   │  │ 3. Searcher Service     │  │         │
│  │  │ 3. Chunker Service      │  │   │  │    (Milvus + ES + RRF)  │  │         │
│  │  │  ┌───────┬───────┬────┐ │  │   │  └───────────┬─────────────┘  │         │
│  │  │  │Unstru-│Struc- │Code│ │  │   │              ▼                │         │
│  │  │  │ctured │tured  │AST │ │  │   │  ┌─────────────────────────┐  │         │
│  │  │  └───────┴───────┴────┘ │  │   │  │ 4. Reranker Service     │  │         │
│  │  └───────────┬─────────────┘  │   │  │    (Optional)           │  │         │
│  │              ▼                │   │  └───────────┬─────────────┘  │         │
│  │  ┌─────────────────────────┐  │   │              ▼                │         │
│  │  │ 4. Embedder Service     │  │   │  ┌─────────────────────────┐  │         │
│  │  │    (Same for all types) │  │   │  │ 5. LLM Service          │  │         │
│  │  └───────────┬─────────────┘  │   │  │    (Generate answer)    │  │         │
│  │              ▼                │   │  └─────────────────────────┘  │         │
│  │  ┌─────────────────────────┐  │   │                               │         │
│  │  │ 5. Indexer Service      │  │   │                               │         │
│  │  │    (Milvus + ES)        │  │   │                               │         │
│  │  └─────────────────────────┘  │   │                               │         │
│  └───────────────┬───────────────┘   └───────────────┬───────────────┘         │
│                  │                                   │                          │
│                  └─────────────────┬─────────────────┘                          │
│                                    ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                         Processing Services                               │   │
│  │                                                                           │   │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐  │   │
│  │  │  Parser   │ │  Chunker  │ │  Embedder │ │  Indexer  │ │  Searcher │  │   │
│  │  │  Service  │ │  Service  │ │  Service  │ │  Service  │ │  Service  │  │   │
│  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘  │   │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐               │   │
│  │  │  Query    │ │  Reranker │ │    LLM    │ │  Content  │               │   │
│  │  │ Processor │ │  Service  │ │  Service  │ │  Router   │               │   │
│  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘               │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                     │                                            │
│                                     ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                            Data Layer                                     │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐             │   │
│  │  │  MinIO    │  │PostgreSQL │  │  Milvus   │  │  Elastic  │             │   │
│  │  │  (Files)  │  │ (Metadata)│  │ (Vector)  │  │  (Text)   │             │   │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘             │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```
---
### Danh sách các thành phần chính và trách nhiệm
**1. UI Layer**
- Cho phép người dùng upload tài liệu và lựa chọn config để xây dựng rag pipeline. 
- Pipeline sẽ dynamic tuỳ theo yêu cầu của người dùng

**2. API Gateway**
- Điểm vào duy nhất (single entry point) của hệ thống. Xử lý routing, rate limiting, authentication sơ bộ, SSL termination, và phân tải request đến các service phía sau.

**3. Logical service**

**3.1. Document handler service**
- Đây là service giúp quản lý luồng đầu vào của dữ liệu khi user upload lên hệ thống
- Khi user bấm upload, request được gửi đến API server. Tại đây hệ thống thực hiện một số bước validate trước khi chấp nhận file
- Sau khi validate thành công, file sẽ được upload vào Object Storage dưới dạng object storage, đảm bảo tên file là unique trong mỗi KB. 
- Quy tắc hiện tại sẽ là: trong 1 KB không được upload 2 file trùng tên với nhau. Tuy nhiên người dùng vẫn có thể upload 1 file trên nhiều KB khác nhau
- Song song với việc lưu file lên object storage, hệ thống tạo một document record trong database để lưu metadata: tên file, loại file, dung lượng, file hash, đường dẫn trên object storage, trạng thái xử lý (đang chờ, đang xử lý, hoàn thành, lỗi), thông tin user sở hữu, và timestamp
- Sau khi file đã nằm an toàn trên object storage và metadata đã được ghi vào database, hệ thống đẩy một message vào hàng đợi (message queue) để thông báo cho processing pipeline rằng có tài liệu mới cần xử lý.  
</br>

**3.2. Queue service**
- Sau khi tài liệu thành công được upload vào Object Storage và ghi lại metadata vào database, request sẽ được đẩy vào queue
- Các worker sẽ nhận request và toàn bộ quá trình nặng phía sau (parse text, chia chunk, tạo embedding, index vào vector store) sẽ được worker xử lý bất đồng bộ 


*Mô tả luồng:*
```
┌──────────┐      ┌─────────┐      ┌─────────┐      ┌──────────┐
│  User    │ ──── │   API   │ ──── │   DB    │      │  Worker  │
└──────────┘      └─────────┘      └─────────┘      └──────────┘
                       │                                  │
                       │          ┌─────────┐             │
                       └───────── │  Queue  │ ────────────┘
                                  └─────────┘
```

</br>

**3.3. Rag component service**
- Gồm các service xử lý data được đặt trong pipeline (ingestion và retrieval) để xử lý dữ liệu qua từng bước, gồm:

| Service | Input | Output | Called By |
|---------|-------|--------|-----------|
| **Parser Service** | File path (Object Storage) | Extracted text | Ingestion Worker |
| **Chunker Service** | Text + Config | Chunks | Ingestion Worker |
| **Embedder Service** | Chunks + Model config | Vectors | Ingestion Worker / Retrieval Worker |
| **Indexer Service** | Chunks + Vectors | Indexed in Milvus/ES | Ingestion Worker |
| **Query Processor** | Query + Config | Processed query | Retrieval Worker |
| **Searcher Service** | Query + Config | Search results | Retrieval Worker |
| **Reranker Service** | Results + Config | Reranked results | Retrieval Worker |
| **LLM Service** | Context + Query | Generated answer | Retrieval Worker |

**3.3. Pipeline service**
- Hệ thống được xây dựng theo hướng `config as pipeline`, nghĩa là từ những lựa chọn của user trên UI, sẽ thành các config tại json file -> gửi vào hệ thống để xây dựng pipeline theo các config đó

**4. Integration Layer**
- Lớp xử lý giao tiếp giữa các service nội bộ và hệ thống bên ngoài. Bao gồm message broker (Kafka, RabbitMQ), event bus, service mesh, và các adapter kết nối 3rd-party API.

**Queue**
- Trong hệ thống này sẽ sử dụng queue để nhận từ API Gateway sau khi lưu data vào Object Storage và push request đến các worker 
- Đây là nơi chịu tải nếu hệ thống nhận nhiều request liên tục

**Adapter**
- Đây là component handle cho luồng đồng bộ dữ liệu từ các hệ thống third party (future plan)

**5. Caching layer**
=> Tăng tốc truy xuất dữ liệu bằng in-memory cache

**Semantic cache**
- So sánh ý nghĩa của query mới với các query đã xử lý trước đó.
- Cách hoạt động: khi user gửi query, hệ thống embed query đó thành vector rồi tìm trong cache xem có query nào tương tự (cosine similarity > threshold, thường 0.95+) đã được trả lời chưa. Nếu có thì trả kết quả cũ luôn, không cần chạy lại toàn bộ pipeline. Ví dụ "Chính sách nghỉ phép là gì?" và "Cho tôi biết về quy định nghỉ phép" sẽ hit cùng một cache entry.

**Chunk cache**
- Cache các chunk đã parse và process sẵn từ raw document. Khi một document được ingest, kết quả sau bước chunking + cleaning được lưu cache. Nếu cần re-process (ví dụ đổi embedding model) thì không cần đọc lại file gốc và chạy lại bước parsing.

**Embedding cache**
- Embedding model là bước tốn latency đáng kể. Cache layer ở đây lưu mapping từ text chunk → vector để tránh gọi embedding model lặp lại cho cùng một đoạn text. Điều này đặc biệt hữu ích khi re-index dữ liệu — chỉ cần embed lại các chunk mới hoặc đã thay đổi, chunk cũ giữ nguyên vector từ cache.
- Tương tự, query embedding cũng được cache. Nếu exact cùng một câu query đã được embed trước đó thì dùng lại vector, không cần gọi API embedding nữa.

**Retrieval cache**
- Sau bước retrieval, kết quả là một danh sách chunk đã sắp xếp theo relevance. Cache layer lưu lại kết quả này theo query (hoặc query vector). Lần sau có query tương tự, bỏ qua bước search vector DB và reranking — hai bước thường chiếm phần lớn latency trong pipeline.
- Cache này cần invalidation strategy rõ ràng: khi dữ liệu nguồn thay đổi (thêm/sửa/xóa document), các cache entry liên quan phải bị xóa hoặc đánh dấu stale. Cách phổ biến là gắn TTL (time-to-live) hoặc invalidate theo document ID khi có cập nhật.

**6. Data storage**
- Sử dụng Object Storage làm Single Source of Truth (SSOT) cho các tài liệu raw. Chúng được lưu dưới dạng object 
- Database được sử dụng để:
    - Lưu metadata của tài liệu, bao gồm document ID, file path, và các thông tin khác.
    - Lưu các thông tin khác trong hệ thống: trạng thái ingestion pipeline (document nào đã process, đang process, lỗi), lineage tracking (chunk nào thuộc document nào, được tạo bởi chunking strategy nào, embed bởi model nào), access control (ai được truy cập document nào), và versioning (lịch sử thay đổi document và re-embedding).
    - Lưu thông tin của người dùng 
- RAG DB lưu vector và text của các chunk. Hệ thống cung cấp khả năng tạo 2 DB nào trong 1 luồng ingestion và có thể sử dụng hybrid search khi retrieve
- In-memory database được sử dụng như cache layer, lưu semantic cache, embedding cache, retrieval result cache

**7. Data governance**
Quản lý các biến đổi về dữ liệu trong hệ thống
- Access Control: đảm bảo việc au được truy cập vào KB và được đọc những tài liệu nào bên trong đó
    - Document level: Mỗi document khi ingest được gắn thông tin quyền truy cập vào metadata — có thể là danh sách user ID được phép, hoặc danh sách role/group. Người dùng khi query sẽ cần thêm 1 bước để check quyền và chỉ query được những document trong quyền hạn
    - KB level: khi tạo KB người tạo sẽ đồng thời gán quyền cho nó. Chỉ những group hoặc user có quyền mới nhìn thấy và truy cập vào được KB
- Data Lineage: Khi RAG trả lời một câu hỏi, user hoặc auditor cần biết: câu trả lời này được tạo ra từ những tài liệu nào, phiên bản nào, được upload bởi ai, vào thời điểm nào, đã qua bao nhiêu bước xử lý.
    - Chunk phải tham chiếu được về document gốc, embedding phải tham chiếu được về chunk, và câu trả lời cuối cùng phải liệt kê được danh sách chunk đã sử dụng.
    - Đảm bảo phải lưu lại pipeline config để có thể truy xuất lại phương pháp tạo
- Data quality control: kiểm soát chất lượng đầu vào
    -  validate xem document có extract được text có ý nghĩa không (không phải toàn ký tự lỗi)
    - kiểm tra trùng lặp (hiện tại chỉ kiểm tra ở mức tên file, người dùng phải tự chịu trách nhiệm với dữ liệu đã upload) 
    - đánh dấu tài liệu lỗi thời cần review hoặc loại bỏ.
- Data lifecycle management: Các trạng thái vòng đời của document
    - Các trạng thái:
        - Pending: khi người dùng upload lên và chưa xử lý
        - Error: khi không vượt qua được bước validate
        - Active: khi tài liệu được sử dụng
        - Inactive: đối với những tài liệu bị xoá 
    - Khi loại tài liệu khỏi vector store nhưng vẫn phải giữ lại bản gốc trên object storage cho mục đích audit
    - Về mặt quản trị, hệ thống sẽ không xoá bất kì tài liệu nào của người dùng, khi người dùng yêu cầu xoá trên UI, thực chất hệ thống chỉ chuyển trạng thái tài liệu sang inactive để người dùng có thể restore khi cần thiết
    - Tuy nhiên với những tài liệu inactive > 30 days, hệ thống sẽ xoá vĩnh viễn
- PII detection và data masking
    - Trước khi chunk text được đưa vào vector store, hệ thống nên scan để phát hiện thông tin cá nhân nhạy cảm (số CMND, số điện thoại, email cá nhân, số tài khoản ngân hàng)
    - Tùy chính sách, thông tin này có thể được mask (thay bằng placeholder), mã hóa, hoặc đánh dấu để chỉ user có quyền mới thấy được.
- Audit Logging
    - Ghi lại mọi hành động liên quan đến dữ liệu: ai upload document nào, ai truy cập document nào qua retrieval, ai xóa hoặc sửa document nào, và ai đã thay đổi quyền truy cập. 
    - Audit log khác với application log ở chỗ nó tập trung vào hành vi con người và quyết định hệ thống, phải immutable (không ai được sửa hoặc xóa), và phải lưu trữ trong thời gian dài (thường vài năm tùy quy định ngành)

**8. Infrastructure**
- Hiện tại cần quickwin để chạy local

**9. Observability Layer**
Mỗi khi user gửi một câu hỏi, hệ thống tạo ra một trace ID xuyên suốt từ đầu đến cuối. Trace này ghi lại từng bước pipeline đã thực thi, thời gian mỗi bước tốn bao lâu, input và output của mỗi bước là gì. Chúng gồm:

- Logging: 
    - HTTP request, error stack trace
    - query gốc là gì? rewrite là gì?
    - thời gian embedding
    - vector search trả về những chunk vào với score bao nhiêu
    - reranker output
    - prompt cuối cùng gửi cho LLM chứa bao nhiêu token
    - LLM trả lời trong bao lâu và tốn bao nhiêu token
(Các công cụ phổ biến cho RAG tracing bao gồm Langfuse (open-source, có thể self-host), LangSmith (của LangChain, SaaS), và Phoenix (của Arize, open-source). Những công cụ này được thiết kế riêng cho LLM pipeline nên hiểu cấu trúc trace của RAG tốt hơn nhiều so với distributed tracing truyền thống như Jaeger hay Zipkin.)
- System metrics:
    - Latency của từng stage trong pipeline (embedding latency, retrieval latency, LLM latency) cho biết bước nào đang là bottleneck. 
    - Throughput (số query xử lý mỗi giây) cho biết hệ thống đang chịu tải bao nhiêu. 
    - Token usage per request giúp kiểm soát chi phí LLM — nếu trung bình mỗi request tốn 3000 token mà đột nhiên nhảy lên 8000, có thể prompt construction đang có vấn đề. 
    - Error rate theo từng stage giúp phát hiện sớm khi một thành phần bắt đầu degraded — ví dụ embedding service bắt đầu timeout nhiều hơn bình thường.


## 3. Technology Stack

| Techstack | Vai trò | Lý do sử dụng |
|---|---|---|
| **MinIO** | Object Storage | MinIO được chọn làm tầng lưu trữ file gốc (PDF, DOCX, hình ảnh…) vì nó hoàn toàn tương thích với S3 API — nghĩa là toàn bộ code tương tác với storage có thể chuyển sang AWS S3 mà không cần sửa đổi gì. Đây là lợi thế lớn cho chiến lược multi-cloud hoặc khi cần migrate từ on-premise lên cloud sau này. So với các giải pháp tương đương như Ceph hoặc SeaweedFS, MinIO vượt trội ở sự đơn giản trong triển khai — chỉ cần một binary duy nhất là có thể chạy được, phù hợp cho cả môi trường dev lẫn production. MinIO cũng hỗ trợ erasure coding và bitrot protection, đảm bảo dữ liệu tài liệu gốc không bị hỏng theo thời gian — điều đặc biệt quan trọng khi tài liệu gốc là nguồn chân lý (source of truth) của toàn bộ hệ thống RAG. Ngoài ra, MinIO có hiệu năng I/O rất cao cho việc đọc/ghi file lớn, giúp quá trình ingestion hàng loạt tài liệu diễn ra nhanh chóng. |
| **PostgreSQL** | Relational Database | PostgreSQL đảm nhận vai trò lưu trữ metadata tài liệu (tiêu đề, nguồn, ngày tạo, trạng thái xử lý), quản lý user, lịch sử truy vấn, và cấu hình hệ thống. Lý do chọn PostgreSQL thay vì MySQL hay một NoSQL database là bởi PostgreSQL cung cấp JSONB — cho phép lưu metadata bán cấu trúc linh hoạt mà vẫn giữ được khả năng query mạnh mẽ với index GIN. Điều này đặc biệt hữu ích khi mỗi loại tài liệu có bộ metadata khác nhau. PostgreSQL cũng hỗ trợ full-text search cơ bản và pgvector extension, tạo ra một phương án fallback nếu cần giảm bớt complexity ở giai đoạn đầu. Quan trọng hơn, PostgreSQL có hệ sinh thái extension cực kỳ phong phú, ACID compliance chặt chẽ, và là một trong những RDBMS open-source đáng tin cậy nhất với hơn 30 năm phát triển — đảm bảo rằng dữ liệu quan trọng của hệ thống luôn nhất quán và an toàn. |
| **Milvus** | Vector Database | Milvus là thành phần cốt lõi cho semantic search trong pipeline RAG — nơi các embedding vectors của tài liệu được lưu trữ và truy vấn. Lý do chọn Milvus thay vì các giải pháp khác như Qdrant, Weaviate, hay Pinecone nằm ở kiến trúc cloud-native với khả năng tách biệt compute và storage, cho phép scale độc lập từng tầng. Milvus hỗ trợ đa dạng thuật toán ANN index (HNSW, IVF_FLAT, IVF_PQ, DiskANN) — mỗi loại phù hợp với từng tradeoff giữa accuracy và latency khác nhau, giúp team linh hoạt tối ưu theo nhu cầu thực tế. Ở quy mô lớn (hàng triệu đến hàng tỷ vectors), Milvus đã được benchmark và chứng minh hiệu năng vượt trội. Milvus cũng hỗ trợ scalar filtering kết hợp với vector search, cho phép thu hẹp phạm vi tìm kiếm theo metadata (ví dụ: chỉ tìm trong tài liệu của phòng ban X, trong khoảng thời gian Y) — một tính năng thiết yếu cho RAG trong môi trường doanh nghiệp. Thêm vào đó, Milvus sử dụng license Apache 2.0, hoàn toàn thân thiện cho sử dụng thương mại. |
| **Elasticsearch** | Full-text Search | Elasticsearch được đưa vào để bổ sung cho Milvus trong chiến lược **hybrid search** — kết hợp semantic search (vector similarity từ Milvus) với keyword search (BM25 từ Elasticsearch). Nghiên cứu thực tế đã chỉ ra rằng hybrid search cho kết quả retrieval chính xác hơn đáng kể so với chỉ dùng một phương pháp đơn lẻ, đặc biệt trong các trường hợp: truy vấn chứa thuật ngữ chuyên ngành, mã số, tên riêng, hoặc khi user cần tìm chính xác một cụm từ cụ thể — những tình huống mà semantic search thuần túy thường bỏ sót. Elasticsearch là lựa chọn hàng đầu cho full-text search nhờ inverted index được tối ưu qua hơn một thập kỷ, hỗ trợ analyzer đa ngôn ngữ (bao gồm tiếng Việt thông qua ICU plugin), và query DSL cực kỳ linh hoạt. Ngoài ra, aggregation engine của Elasticsearch còn hỗ trợ các tính năng analytics hữu ích như thống kê truy vấn phổ biến, phân tích xu hướng tìm kiếm — dữ liệu quý giá để liên tục cải thiện chất lượng RAG. |
| **Redis** | Cache + Message Queue | Redis đóng hai vai trò quan trọng trong hệ thống. **Vai trò 1 - Caching:** Redis cache kết quả retrieval và response cho những truy vấn phổ biến, giúp thời gian phản hồi giảm từ hàng trăm milliseconds xuống còn dưới 1ms. Redis cũng cache embedding vectors của các truy vấn gần đây, tránh việc gọi lại embedding model. Ngoài ra còn phục vụ session management, rate limiting, và thống kê real-time. **Vai trò 2 - Message Queue:** Sử dụng Redis Streams để điều phối pipeline xử lý bất đồng bộ (document upload → parsing → chunking → embedding → indexing). Redis Streams hỗ trợ consumer groups, message persistence, và acknowledgment — đủ cho workload RAG service ở quy mô vừa (< 500K docs/day). Lý do chọn Redis thay vì message broker riêng (Kafka, RabbitMQ, NATS) là để giảm số lượng components cần vận hành — chỉ cần 1 Redis instance phục vụ cả caching lẫn queuing. Khi cần scale lên > 1M docs/day, có thể migrate sang NATS/Kafka với abstraction layer đã thiết kế sẵn. |


*Lưu ý: Bảng phân tích này dựa trên ngữ cảnh xây dựng hệ thống RAG self-hosted. Nếu chuyển sang môi trường cloud-managed, một số lựa chọn có thể thay đổi (ví dụ: S3 thay MinIO, Amazon OpenSearch thay Elasticsearch).*

## 4. Data Architecture

### Domain Model Overview
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DOMAIN MODEL                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ┌──────────┐       ┌──────────────────┐       ┌──────────────────┐            │
│   │  Tenant  │──1:N──│  Knowledge Base  │──1:N──│    Document      │            │
│   └──────────┘       └──────────────────┘       └────────┬─────────┘            │
│        │                      │                          │                       │
│        │                      │                     1:N  │                       │
│        │               1:1    │                          ▼                       │
│        │                      │                 ┌──────────────────┐             │
│        │                      ▼                 │     Chunk        │             │
│        │             ┌──────────────────┐       └──────────────────┘             │
│        │             │ Pipeline Config  │                                        │
│        │             │ (Ingestion +     │                                        │
│        │             │  Retrieval)      │                                        │
│        │             └──────────────────┘                                        │
│        │                                                                         │
│        └──1:N──┐                                                                 │
│                ▼                                                                 │
│        ┌──────────────────┐       ┌──────────────────┐                          │
│        │      User        │──M:N──│      Group       │                          │
│        └──────────────────┘       └──────────────────┘                          │
│                │                                                                 │
│                └───────── Roles & Permissions ─────────┘                        │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Chiến lược lưu trữ

| Storage Type | Công nghệ | Dữ liệu lưu trữ |
|--------------|-----------|-----------------|
| **Relational** | PostgreSQL | Metadata (users, KBs, documents, pipeline configs, audit logs) |
| **Object Storage** | MinIO | Raw files (PDF, DOCX, images) - Single Source of Truth |
| **Vector DB** | Milvus | Embedding vectors cho semantic search |
| **Search Engine** | Elasticsearch | Full-text index cho keyword search |
| **Cache + Queue** | Redis | Session, semantic cache, embedding cache, rate limiting + Message Queue (Redis Streams) |

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW                                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  INGESTION FLOW:                                                                │
│  ┌────────┐    ┌────────┐    ┌─────────┐    ┌─────────┐    ┌─────────────────┐ │
│  │ Upload │───▶│ MinIO  │───▶│  Parse  │───▶│  Chunk  │───▶│    Embed +      │ │
│  │        │    │(store) │    │         │    │         │    │    Index        │ │
│  └────────┘    └────────┘    └─────────┘    └─────────┘    └─────────────────┘ │
│                     │                                              │            │
│                     ▼                                              ▼            │
│              ┌────────────┐                              ┌─────────────────┐   │
│              │ PostgreSQL │                              │ Milvus + ES     │   │
│              │ (metadata) │                              │ (vectors+text)  │   │
│              └────────────┘                              └─────────────────┘   │
│                                                                                  │
│  RETRIEVAL FLOW:                                                                │
│  ┌────────┐    ┌─────────┐    ┌───────────────┐    ┌─────────┐    ┌─────────┐ │
│  │ Query  │───▶│  Embed  │───▶│ Hybrid Search │───▶│ Rerank  │───▶│   LLM   │ │
│  │        │    │ Query   │    │ (Milvus + ES) │    │(option) │    │ Answer  │ │
│  └────────┘    └─────────┘    └───────────────┘    └─────────┘    └─────────┘ │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Integration & Communication

### Giao tiếp nội bộ

| Pattern | Use Case | Implementation |
|---------|----------|----------------|
| **Sync (REST)** | Query API, Management API | FastAPI endpoints với response time < 500ms |
| **Async (Queue)** | Document ingestion, Batch processing | Redis Streams với consumer groups, workers auto-scale |

**Quy tắc thiết kế:**
- 2 streams chính: `ingestion_queue` và `retrieval_queue`
- Workers xử lý sequential trong mỗi job (không queue giữa các bước)
- Services stateless để dễ scale
- Abstraction layer để dễ migrate sang NATS/Kafka nếu cần scale > 500K docs/day

### Message Queue Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         MESSAGE QUEUE PATTERN                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   API Server                      Queue                        Workers           │
│  ┌──────────┐              ┌───────────────┐              ┌──────────────┐      │
│  │ Validate │──────────────│ Redis Streams │──────────────│   Worker     │      │
│  │ + Store  │   XADD       │               │  XREADGROUP  │   Pool       │      │
│  │ + Return │◀─────────────│  • job_id     │◀─────────────│   (HPA)      │      │
│  │ job_id   │   immediate  │  • consumer   │   + XACK     │              │      │
│  └──────────┘              │    groups     │              └──────────────┘      │
│                            └───────────────┘                                    │
│                                                                                  │
│   Benefits:                                                                      │
│   • Non-blocking uploads (user không cần chờ processing)                        │
│   • Horizontal scaling workers khi load tăng                                    │
│   • Retry mechanism cho failed jobs                                             │
│   • Job cancellation support                                                    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Tích hợp hệ thống bên ngoài cho nguồn đầu vào (future plan)

| External System | Integration Method | Purpose |
|-----------------|-------------------|---------|
| **LLM Provider** | REST API (OpenAI-compatible) | Text generation, Query expansion |
| **Embedding Service** | REST API | Vector embedding |
| **GitHub** | Adapter + Webhook | Document sync from repos |
| **Confluence** | Adapter (future) | Document sync from wiki |

### API Design Principles

- RESTful API với versioning (`/api/v1/...`)
- Swagger documentation
- Rate limiting per tenant
- Request validation với Pydantic schemas

---

## 6. Infrastructure & Deployment

### Deployment Architecture (On-Premise)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        ON-PREMISE DEPLOYMENT                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   Load Balancer (NGINX/HAProxy)                                                 │
│          │                                                                       │
│          ▼                                                                       │
│   ┌──────────────────────────────────────────────────────────────────────────┐  │
│   │                        Application Layer                                  │  │
│   │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐             │  │
│   │  │  API Service   │  │  API Service   │  │  API Service   │  (replicas) │  │
│   │  └────────────────┘  └────────────────┘  └────────────────┘             │  │
│   │                                                                          │  │
│   │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐             │  │
│   │  │Ingestion Worker│  │Ingestion Worker│  │Retrieval Worker│  (scalable) │  │
│   │  └────────────────┘  └────────────────┘  └────────────────┘             │  │
│   └──────────────────────────────────────────────────────────────────────────┘  │
│          │                                                                       │
│          ▼                                                                       │
│   ┌──────────────────────────────────────────────────────────────────────────┐  │
│   │                          Data Layer                                       │  │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │  │
│   │  │PostgreSQL│  │  MinIO   │  │  Milvus  │  │   ES     │  │  Redis   │  │  │
│   │  │(Primary+ │  │(Cluster) │  │(Cluster) │  │(Cluster) │  │(Sentinel)│  │  │
│   │  │ Replica) │  │          │  │          │  │          │  │          │  │  │
│   │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │  │
│   └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Container Orchestration

| Component | Deployment Strategy | Scaling |
|-----------|--------------------| --------|
| **API Services** | Deployment (replicas: 2-3) | Manual / HPA based on CPU |
| **Workers** | Deployment (min: 2) | HPA based on queue depth |
| **Databases** | StatefulSet | Vertical scaling |
| **Queue** | StatefulSet with persistence | Sentinel for HA |

### Environments

| Environment | Purpose | Characteristics |
|-------------|---------|-----------------|
| **Development** | Local testing | Docker Compose, single instance |
| **Staging** | Integration testing | Kubernetes, scaled down |
| **Production** | Live system | Kubernetes, full HA, monitoring |

### CI/CD Pipeline Overview

```
Code Push → Build → Unit Tests → Container Build → Deploy Staging → Integration Tests → Deploy Production
```

---

## 7. Security

### Authentication & Authorization

**Authentication:**
- JWT-based authentication
- Token refresh mechanism
- Session management với Redis

**Authorization (RBAC):**

| Role | Permissions |
|------|-------------|
| **Admin** | Full system access, tenant management |
| **KB Builder** | Create/manage KBs, configure pipelines, upload documents |
| **General User** | Query KBs được cấp quyền |

**Permission Levels:**
- **Tenant Level**: Isolation giữa các tenants
- **KB Level**: Ai được query KB nào
- **Document Level**: Fine-grained access control (public/private/custom)

### Data Protection

| Aspect | Implementation |
|--------|----------------|
| **Encryption at Rest** | MinIO encryption, PostgreSQL TDE (optional) |
| **Encryption in Transit** | TLS 1.3 cho tất cả connections |
| **Secrets Management** | Environment variables / Kubernetes Secrets |
| **PII Handling** | Detection và masking trước khi index (configurable) |

### Security Controls

| Control | Description |
|---------|-------------|
| **Input Validation** | Schema validation cho tất cả API inputs |
| **Rate Limiting** | Per-tenant rate limits để chống abuse |
| **Audit Logging** | Ghi lại mọi actions quan trọng (upload, delete, access) |
| **File Validation** | Check file type, size limits, malware scan (optional) |

---

## 8. Non-Functional Requirements

### Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| **Query Latency (P95)** | < 3s | Bao gồm retrieval + LLM generation |
| **Upload Response** | < 500ms | Trả về job_id, processing async |
| **Ingestion Throughput** | 100 docs/hour/worker | Phụ thuộc document size |
| **Concurrent Users** | 100+ per tenant | Với resource allocation phù hợp |

### Scalability Strategy

| Component | Horizontal | Vertical |
|-----------|------------|----------|
| **API Services** | ✅ Stateless, load balanced | ✅ |
| **Workers** | ✅ Auto-scale by queue | ✅ |
| **PostgreSQL** | Read replicas | ✅ Primary |
| **Milvus** | ✅ Distributed mode | ✅ |
| **Elasticsearch** | ✅ Cluster sharding | ✅ |

### Availability & Disaster Recovery

| Aspect | Strategy |
|--------|----------|
| **Target Availability** | 99.5% (planned downtime excluded) |
| **Database Backup** | Daily full backup, continuous WAL archiving |
| **Object Storage** | MinIO erasure coding, cross-site replication (optional) |
| **Recovery Point Objective (RPO)** | < 1 hour |
| **Recovery Time Objective (RTO)** | < 4 hours |

### Monitoring & Alerting

| Layer | Tools | Metrics |
|-------|-------|---------|
| **Infrastructure** | Prometheus + Grafana | CPU, Memory, Disk, Network |
| **Application** | Custom metrics, Structured logging | Request latency, Error rates, Queue depth |
| **RAG Pipeline** | Langfuse / Phoenix (optional) | Retrieval quality, Token usage, LLM latency |

**Key Alerts:**
- Error rate > 5%
- Queue depth > 1000 pending jobs
- Latency P95 > SLA threshold
- Storage usage > 80%

---

## 9. Risks & Trade-offs

### Kiến trúc Trade-offs đã chấp nhận

| Decision | Trade-off | Rationale |
|----------|-----------|-----------|
| **Redis Streams (không dùng Kafka/NATS)** | Giới hạn ~500K docs/day, ít features hơn | Giảm components, đơn giản vận hành, đủ cho quickwin |
| **2 Streams Only** | Giảm flexibility cho phức tạp routing | Đơn giản hóa, giảm operational overhead |
| **Sequential Service Calls** | Không tối ưu cho parallel processing | Dễ debug, dễ hiểu, phù hợp throughput hiện tại |
| **No Document Versioning (MVP)** | User tự quản lý versions | Đơn giản hóa, triển khai nhanh |
| **Soft Delete 30 days** | Tốn storage | Cho phép restore, compliance |
| **Single Embedding Model per KB** | Không mix models | Consistency trong retrieval quality |

### Rủi ro chính và giảm thiểu

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **LLM Provider Downtime** | High | Medium | Fallback provider, graceful degradation |
| **Vector DB Corruption** | High | Low | Regular backups, re-indexing capability |
| **Queue Overflow** | Medium | Medium | Rate limiting, auto-scaling workers |
| **Storage Exhaustion** | High | Low | Monitoring alerts, quota per tenant |
| **Embedding Model Change** | Medium | Medium | Re-indexing pipeline, backward compatibility |

### Technical Debt đã biết

| Item | Description | Priority to Address |
|------|-------------|---------------------|
| **No Circuit Breaker** | External service calls không có circuit breaker | P1 - trước production |
| **Basic Retry Logic** | Chưa có exponential backoff đầy đủ | P2 |
| **Limited Caching** | Chưa implement đầy đủ semantic cache | P2 |
| **Manual Scaling** | Worker scaling chưa fully automated | P2 |
| **No Distributed Tracing** | Khó debug cross-service issues | P3 |

---

*Lưu ý: Tài liệu này cung cấp cái nhìn high-level về kiến trúc hệ thống. Chi tiết implementation và configuration được mô tả trong các tài liệu Solution Design chi tiết.*
