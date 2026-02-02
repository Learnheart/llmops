# Business Analysis Documents
# RAG Service QuickWin

## Overview

Thư mục này chứa các tài liệu nghiệp vụ (Business Analysis) cho dự án RAG Service QuickWin. Các tài liệu này định nghĩa **"hệ thống cần làm gì và cho ai"**, làm nền tảng để:
- Developer biết mình đang build cái gì
- Tester biết mình đang test cái gì
- Stakeholder biết mình đang nhận được cái gì

## Document Index

| # | Document | Description | Status |
|---|----------|-------------|--------|
| 1 | [PRD - Product Requirements](./PRD-RAG-Service-QuickWin.md) | Tài liệu nền tảng: vision, personas, goals, scope, success metrics | Draft |
| 2 | [FRS - Functional Requirements](./FRS-RAG-Service-QuickWin.md) | Chi tiết yêu cầu chức năng: input/output, validation, acceptance criteria | Draft |
| 3 | [User Stories](./UserStories-RAG-Service-QuickWin.md) | User stories với acceptance criteria dạng Gherkin, journey maps | Draft |
| 4 | [Wireframes](./Wireframes-RAG-Service-QuickWin.md) | Mô tả giao diện, layouts, components, states | Draft |

## Reading Order

```
1. PRD (Hiểu bài toán)
   └── 2. FRS (Hiểu chi tiết requirements)
       └── 3. User Stories (Hiểu context sử dụng)
           └── 4. Wireframes (Hiểu UI/UX)
```

## Document Relationships

```
                    ┌─────────────────┐
                    │       PRD       │
                    │  (What & Why)   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
      ┌───────────┐   ┌───────────┐   ┌───────────┐
      │    FRS    │   │   User    │   │Wireframes │
      │  (How)    │   │  Stories  │   │  (Look)   │
      └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
            │               │               │
            └───────────────┼───────────────┘
                            ▼
                    ┌───────────────┐
                    │  Detailed     │
                    │  Design (SA)  │
                    └───────────────┘
```

## Related Documents

| Document | Location | Description |
|----------|----------|-------------|
| High-Level Design | [../SA/rag_highlevel.md](../SA/rag_highlevel.md) | Kiến trúc kỹ thuật tổng quan |
| Detailed Design Docs | [../SA/Detailed_design_documents/](../SA/Detailed_design_documents/) | Chi tiết thiết kế kỹ thuật |

## Version History

| Version | Date | Author | Summary |
|---------|------|--------|---------|
| 1.0 | 2026-02-02 | BA Team | Initial release of all BA documents |

## How to Use These Documents

### For Product Owner
- Review PRD for vision alignment
- Validate User Stories cover all use cases
- Sign off on FRS acceptance criteria

### For Developers
- Start with User Stories to understand context
- Refer to FRS for detailed requirements
- Use Wireframes for UI implementation

### For QA Team
- Use FRS acceptance criteria for test case design
- Reference Wireframes for UI testing
- Use User Stories for end-to-end test scenarios

### For UX/UI Designers
- Use Wireframes as starting point
- Refer to PRD for design principles
- Validate designs against User Stories

---

**Questions?** Contact the BA Team or Product Owner.
