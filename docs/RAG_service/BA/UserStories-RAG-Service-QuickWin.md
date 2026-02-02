# User Stories
# RAG Service QuickWin

| Metadata | Value |
|----------|-------|
| **Document ID** | US-RAG-001 |
| **Version** | 1.0 |
| **Status** | Draft |
| **PRD Reference** | PRD-RAG-001 |
| **FRS Reference** | FRS-RAG-001 |
| **Owner** | Business Analyst |
| **Last Updated** | 2026-02-02 |

---

## 1. Introduction

### 1.1 Purpose
Tài liệu này chứa các User Stories được viết từ góc nhìn người dùng, giúp development team hiểu context sử dụng thực tế và đảm bảo implementation phù hợp với nhu cầu business.

### 1.2 Story Format
```
Là [persona],
Tôi muốn [action/feature],
Để [benefit/value].
```

### 1.3 Story Point Scale
| Points | Complexity | Example |
|--------|------------|---------|
| 1 | Trivial | UI label change |
| 2 | Simple | Add validation rule |
| 3 | Moderate | New API endpoint |
| 5 | Complex | New module with logic |
| 8 | Very Complex | Major feature with integrations |
| 13 | Epic | Needs breaking down |

---

## 2. Epic Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          EPIC STRUCTURE                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  EPIC 1: Knowledge Base Setup                                       │
│  ├── US-001: Create Knowledge Base                                  │
│  ├── US-002: Upload Documents                                       │
│  ├── US-003: Configure Pipeline                                     │
│  └── US-004: Monitor Processing                                     │
│                                                                      │
│  EPIC 2: Knowledge Query                                            │
│  ├── US-005: Ask Questions                                          │
│  ├── US-006: View Sources                                           │
│  └── US-007: Provide Feedback                                       │
│                                                                      │
│  EPIC 3: Knowledge Management                                       │
│  ├── US-008: Manage Documents                                       │
│  ├── US-009: Update KB Settings                                     │
│  └── US-010: Trash & Recovery                                       │
│                                                                      │
│  EPIC 4: User Access                                                │
│  ├── US-011: Authentication                                         │
│  └── US-012: Session Management                                     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Epic 1: Knowledge Base Setup

### US-001: Create Knowledge Base

**Story**
```
Là một HR Manager,
Tôi muốn tạo một Knowledge Base mới cho các chính sách công ty,
Để nhân viên có thể tự tra cứu thay vì hỏi HR trực tiếp.
```

| Attribute | Value |
|-----------|-------|
| **Priority** | P0 |
| **Story Points** | 3 |
| **Sprint** | MVP Sprint 1 |
| **FRS Reference** | FR-KB-001 |

**Acceptance Criteria**:
```gherkin
Feature: Create Knowledge Base

  Scenario: Successfully create a new Knowledge Base
    Given I am logged in as "hr.manager@company.com"
    And I am on the Knowledge Base list page
    When I click "Create New Knowledge Base"
    And I enter name "HR Policies 2026"
    And I enter description "All company policies and procedures"
    And I click "Create"
    Then I should see success message "Knowledge Base created successfully"
    And I should be on the KB detail page
    And I should see empty document list with "Upload your first document" prompt
    And KB should have default pipeline configuration

  Scenario: Duplicate name validation
    Given I am logged in as "hr.manager@company.com"
    And a KB named "HR Policies" already exists
    When I try to create KB with name "HR Policies"
    Then I should see error "A Knowledge Base with this name already exists"
    And no KB should be created

  Scenario: Name validation
    Given I am logged in as "hr.manager@company.com"
    When I try to create KB with empty name
    Then "Create" button should be disabled
    And I should see hint "Name is required (3-100 characters)"
```

**Developer Notes**:
- KB được tạo với default pipeline config (xem FRS FR-PC-001)
- Không cần wizard multi-step - single form đủ đơn giản
- Consider auto-suggest name based on first uploaded document (future)

---

### US-002: Upload Documents

**Story**
```
Là một HR Manager,
Tôi muốn upload toàn bộ policy documents lên KB,
Để hệ thống có thể index và trả lời câu hỏi từ nội dung này.
```

| Attribute | Value |
|-----------|-------|
| **Priority** | P0 |
| **Story Points** | 5 |
| **Sprint** | MVP Sprint 1 |
| **FRS Reference** | FR-UP-001 to FR-UP-004 |

**Acceptance Criteria**:
```gherkin
Feature: Upload Documents

  Scenario: Upload single document via button
    Given I am on KB "HR Policies" detail page
    When I click "Upload" button
    And I select file "employee_handbook.pdf" (5MB)
    Then I should see upload progress bar
    And upload should complete within reasonable time
    And I should see document in list with status "Processing"

  Scenario: Drag and drop multiple documents
    Given I am on KB "HR Policies" detail page
    When I drag 5 PDF files onto the upload zone
    Then all 5 files should start uploading
    And I should see individual progress for each file
    And completed files should appear in document list immediately

  Scenario: Upload unsupported file type
    Given I am on KB "HR Policies" detail page
    When I try to upload "script.exe"
    Then I should see error "File type .exe is not supported"
    And file should not be uploaded

  Scenario: Upload file exceeding size limit
    Given I am on KB "HR Policies" detail page
    When I try to upload "large_video.mp4" (100MB)
    Then I should see error "File size exceeds maximum limit of 50MB"

  Scenario: Handle duplicate filename
    Given KB "HR Policies" already has "policy.pdf"
    When I upload another file named "policy.pdf"
    Then I should see dialog with options:
      | Option      | Description                    |
      | Replace     | Overwrite existing document    |
      | Keep Both   | Rename to "policy (1).pdf"     |
      | Cancel      | Cancel this upload             |
```

**UX Considerations**:
- Upload zone nên chiếm prominent space - đây là primary action khi KB mới tạo
- Drag & drop hover state cần rõ ràng (border change, background color)
- Progress indicator phải responsive - user cần biết hệ thống đang hoạt động
- Cho phép user navigate away - upload continues in background

---

### US-003: Configure Pipeline (No-Code)

**Story**
```
Là một Business Analyst có hiểu biết cơ bản về AI,
Tôi muốn điều chỉnh cách hệ thống xử lý documents và trả lời câu hỏi,
Để optimize kết quả cho use case cụ thể của tôi mà không cần viết code.
```

| Attribute | Value |
|-----------|-------|
| **Priority** | P0 |
| **Story Points** | 8 |
| **Sprint** | MVP Sprint 2 |
| **FRS Reference** | FR-PC-001 to FR-PC-007 |

**Acceptance Criteria**:
```gherkin
Feature: Configure Pipeline

  Scenario: View current configuration
    Given I am on KB "HR Policies" settings page
    When I click "Pipeline Configuration" tab
    Then I should see current settings organized in sections:
      | Section    | Settings                          |
      | Chunking   | Strategy, Size, Overlap           |
      | Search     | Type, Weights, Top K              |
      | Reranker   | Enabled/Disabled, Model, Top N    |
      | LLM        | Model, Temperature, System Prompt |
    And each setting should show current value and description

  Scenario: Adjust search weights with slider
    Given I am on Pipeline Configuration page
    When I drag the "Vector/Keyword Balance" slider
    Then I should see vector_weight and keyword_weight update in real-time
    And values should always sum to 1.0
    And I should see visual indicator of what each extreme means

  Scenario: Save configuration changes
    Given I have modified chunking strategy to "paragraph"
    When I click "Save Changes"
    Then I should see confirmation "Configuration saved"
    And I should see warning "Existing documents will be re-processed"
    When I confirm
    Then documents should be queued for re-processing

  Scenario: Use preset configuration
    Given I am on Pipeline Configuration page
    When I click "Use Preset"
    And I select "Precision" preset
    Then all settings should update to preset values
    And I should see description of what this preset optimizes for

  Scenario: Reset to defaults
    Given I have customized pipeline configuration
    When I click "Reset to Defaults"
    Then I should see confirmation dialog
    When I confirm
    Then all settings should revert to system defaults
```

**UX Considerations**:
- Mỗi setting cần có tooltip explaining what it does in simple terms
- Show "impact indicator" - e.g., "Higher overlap = better context but slower processing"
- Group related settings visually
- "Advanced" toggle để ẩn complex settings for basic users
- Preview/test option: "Try a query with these settings" before saving

---

### US-004: Monitor Document Processing

**Story**
```
Là một HR Manager vừa upload 50 policy documents,
Tôi muốn biết trạng thái processing của từng document,
Để tôi biết khi nào có thể bắt đầu sử dụng hệ thống.
```

| Attribute | Value |
|-----------|-------|
| **Priority** | P1 |
| **Story Points** | 3 |
| **Sprint** | MVP Sprint 1 |
| **FRS Reference** | FR-UP-003 |

**Acceptance Criteria**:
```gherkin
Feature: Monitor Processing Status

  Scenario: View processing status in document list
    Given I have uploaded 10 documents
    When I view the document list
    Then each document should show status badge:
      | Status     | Badge Color | Description        |
      | Pending    | Gray        | Waiting in queue   |
      | Processing | Blue        | Currently indexing |
      | Ready      | Green       | Available for query|
      | Failed     | Red         | Processing failed  |

  Scenario: View overall progress
    Given 10 documents are being processed
    When I view KB detail page
    Then I should see summary "7/10 documents ready"
    And I should see progress bar

  Scenario: Handle failed document
    Given document "corrupted.pdf" failed processing
    When I click on the document
    Then I should see error message explaining what went wrong
    And I should see "Retry" button
    When I click "Retry"
    Then document should be re-queued for processing

  Scenario: Real-time status updates
    Given I am viewing document list with processing documents
    When a document finishes processing
    Then status should update automatically without page refresh
    And I should see brief notification "handbook.pdf is now ready"
```

**Technical Notes**:
- Use WebSocket or SSE for real-time updates
- Consider batching notifications to avoid spam
- Failed documents should show actionable error messages, not technical stack traces

---

## 4. Epic 2: Knowledge Query

### US-005: Ask Questions

**Story**
```
Là một nhân viên mới,
Tôi muốn hỏi câu hỏi về chính sách công ty bằng ngôn ngữ tự nhiên,
Để tôi có thể tìm được thông tin cần thiết mà không cần đọc qua 50 trang handbook.
```

| Attribute | Value |
|-----------|-------|
| **Priority** | P0 |
| **Story Points** | 5 |
| **Sprint** | MVP Sprint 2 |
| **FRS Reference** | FR-QI-001 |

**Acceptance Criteria**:
```gherkin
Feature: Ask Questions

  Scenario: Ask a simple question
    Given I am on Query page of KB "HR Policies"
    And KB has ready documents
    When I type "How many vacation days do I get per year?"
    And I press Enter
    Then I should see loading indicator
    And I should receive answer within 5 seconds
    And answer should include specific information from documents
    And I should see source references below answer

  Scenario: Follow-up question
    Given I just asked about vacation days
    When I ask "What about sick leave?"
    Then system should understand context from previous question
    And provide relevant answer about sick leave

  Scenario: Question with no relevant content
    Given KB only contains HR policies
    When I ask "What is the weather today?"
    Then I should see message "I couldn't find relevant information..."
    And I should NOT see hallucinated answer

  Scenario: KB has no ready documents
    Given I am on Query page of KB with only processing documents
    When I try to type a question
    Then input should be disabled
    And I should see "Documents are still processing. Please wait."
    And I should see processing progress indicator

  Scenario: Empty query submission
    Given I am on Query page
    When I click Send without typing anything
    Then nothing should happen (button disabled when empty)
```

**UX Considerations**:
- Input field placeholder: "Ask a question about [KB name]..."
- Send button và Enter key để submit
- Auto-focus on input when page loads
- Show typing indicator while waiting for response
- Markdown rendering for formatted answers
- Copy button on answer

---

### US-006: View Source References

**Story**
```
Là một Compliance Officer,
Tôi muốn xem chính xác câu trả lời được lấy từ đâu trong documents,
Để tôi có thể verify accuracy và cite source khi cần.
```

| Attribute | Value |
|-----------|-------|
| **Priority** | P0 |
| **Story Points** | 3 |
| **Sprint** | MVP Sprint 2 |
| **FRS Reference** | FR-QI-002 |

**Acceptance Criteria**:
```gherkin
Feature: View Source References

  Scenario: View sources after getting answer
    Given I received an answer to my question
    When I look below the answer
    Then I should see "Sources" section with list of references
    And each source should show:
      | Element         | Example                    |
      | Document name   | "employee_handbook.pdf"    |
      | Content preview | "Section 3.2: Vacation..." |
      | Relevance       | Visual indicator (high/med)|
      | Page number     | "Page 12" (if available)   |

  Scenario: Expand source to see full context
    Given I see a source reference
    When I click on the source card
    Then I should see expanded view with full chunk content
    And relevant text should be highlighted
    And I should see "Open Original Document" button

  Scenario: Open original document
    Given I have expanded a source
    When I click "Open Original Document"
    Then I should be able to view/download the original file
    And jump to relevant page/section if possible

  Scenario: Multiple sources
    Given answer was generated from 5 source chunks
    When I view sources
    Then I should see top 3 sources initially
    And I should see "Show 2 more sources" link
    When I click it
    Then all 5 sources should be visible
```

**UX Considerations**:
- Sources help build trust - make them prominent but not overwhelming
- Inline citations in answer text (e.g., [1], [2]) linked to sources below
- Hover on citation shows tooltip with preview

---

### US-007: Provide Feedback on Answers

**Story**
```
Là một Product Owner,
Tôi muốn đánh giá chất lượng câu trả lời,
Để hệ thống có thể cải thiện theo thời gian và team biết accuracy hiện tại.
```

| Attribute | Value |
|-----------|-------|
| **Priority** | P1 |
| **Story Points** | 2 |
| **Sprint** | MVP Sprint 3 |
| **FRS Reference** | FR-QI-003 |

**Acceptance Criteria**:
```gherkin
Feature: Feedback on Answers

  Scenario: Rate answer as helpful
    Given I received a good answer
    When I click thumbs up icon
    Then icon should be highlighted (selected state)
    And my feedback should be recorded
    And I should see brief "Thanks for feedback!" message

  Scenario: Rate answer as not helpful
    Given I received a poor answer
    When I click thumbs down icon
    Then I should see optional feedback form
    With quick options:
      | Option              |
      | Answer was wrong    |
      | Answer was incomplete|
      | Sources were irrelevant|
      | Other               |
    And optional text field for details
    When I submit feedback
    Then my feedback should be recorded

  Scenario: Change rating
    Given I rated answer as helpful
    When I click thumbs down
    Then rating should switch to not helpful
    And previous rating should be overwritten
```

---

## 5. Epic 3: Knowledge Management

### US-008: Manage Documents in KB

**Story**
```
Là một HR Manager,
Tôi muốn quản lý documents đã upload (xem, xóa, thay thế),
Để KB luôn chứa thông tin up-to-date và chính xác.
```

| Attribute | Value |
|-----------|-------|
| **Priority** | P0 |
| **Story Points** | 5 |
| **Sprint** | MVP Sprint 2 |
| **FRS Reference** | FR-DM-001 to FR-DM-006 |

**Acceptance Criteria**:
```gherkin
Feature: Manage Documents

  Scenario: View document list with details
    Given I am on KB "HR Policies" document page
    Then I should see table/list with columns:
      | Column      | Sortable | Filterable |
      | Name        | Yes      | Search     |
      | Status      | Yes      | Yes        |
      | Size        | Yes      | No         |
      | Uploaded At | Yes      | Date range |
      | Uploaded By | Yes      | Yes        |

  Scenario: Search documents
    Given KB has 50 documents
    When I type "vacation" in search box
    Then list should filter to show only documents with "vacation" in name

  Scenario: Delete single document
    Given I am viewing document list
    When I click delete icon on "old_policy.pdf"
    Then I should see confirmation "Delete old_policy.pdf?"
    And warning "Document will be moved to Trash"
    When I confirm
    Then document should disappear from list
    And I should see "Document moved to Trash. Undo?" toast

  Scenario: Batch delete documents
    Given I am viewing document list
    When I check 5 documents using checkboxes
    Then "Delete Selected (5)" button should appear
    When I click it and confirm
    Then all 5 documents should be moved to Trash

  Scenario: Retry failed document
    Given "corrupted.pdf" shows status "Failed"
    When I click "Retry" action
    Then status should change to "Pending"
    And document should be re-queued for processing
```

---

### US-009: Update KB Settings

**Story**
```
Là owner của KB,
Tôi muốn edit thông tin KB (tên, mô tả) và delete KB khi không cần nữa,
Để tôi có full control over my knowledge base.
```

| Attribute | Value |
|-----------|-------|
| **Priority** | P0 |
| **Story Points** | 2 |
| **Sprint** | MVP Sprint 2 |
| **FRS Reference** | FR-KB-003 to FR-KB-005 |

**Acceptance Criteria**:
```gherkin
Feature: Update KB Settings

  Scenario: Edit KB name and description
    Given I am owner of KB "HR Policies"
    When I go to Settings tab
    And I change name to "HR Documentation 2026"
    And I click Save
    Then KB should be renamed
    And I should see confirmation

  Scenario: Delete KB
    Given I am owner of KB "HR Policies" with 10 documents
    When I click "Delete Knowledge Base"
    Then I should see warning dialog:
      """
      Deleting "HR Policies" will:
      - Move all 10 documents to Trash
      - Remove all configurations
      - Make the KB unavailable for queries

      This can be undone within 30 days from Trash.
      Type "HR Policies" to confirm.
      """
    When I type the KB name and click Delete
    Then KB should be moved to Trash
    And I should be redirected to KB list

  Scenario: Non-owner cannot delete
    Given I have "contributor" role on KB "HR Policies"
    When I view KB settings
    Then "Delete Knowledge Base" option should not be visible
```

---

### US-010: Trash and Recovery

**Story**
```
Là một user đã accidentally delete một document quan trọng,
Tôi muốn recover nó từ Trash,
Để tôi không mất dữ liệu do sai sót.
```

| Attribute | Value |
|-----------|-------|
| **Priority** | P1 |
| **Story Points** | 3 |
| **Sprint** | MVP Sprint 3 |
| **FRS Reference** | FR-TR-001 to FR-TR-005 |

**Acceptance Criteria**:
```gherkin
Feature: Trash and Recovery

  Scenario: View Trash contents
    Given I have deleted some documents and KBs
    When I go to Trash page
    Then I should see two sections: "Knowledge Bases" and "Documents"
    And each item should show:
      | Field             | Example                    |
      | Name              | "old_policy.pdf"           |
      | Original location | "HR Policies"              |
      | Deleted on        | "Feb 1, 2026"              |
      | Days remaining    | "29 days until permanent deletion" |

  Scenario: Restore document
    Given "important_doc.pdf" is in Trash
    When I click "Restore"
    Then document should be restored to original KB
    And document should be available for queries (if was ready before)
    And I should see confirmation "Document restored to HR Policies"

  Scenario: Restore KB with all documents
    Given KB "HR Policies" is in Trash with 10 documents
    When I click "Restore"
    Then KB and all its documents should be restored
    And KB should appear in my KB list

  Scenario: Permanently delete from Trash
    Given "old_doc.pdf" is in Trash
    When I click "Delete Permanently"
    Then I should see warning "This cannot be undone"
    When I confirm
    Then document should be permanently deleted
    And it should no longer appear anywhere

  Scenario: Auto-purge notification
    Given "old_doc.pdf" has 3 days remaining
    When I view Trash
    Then I should see "old_doc.pdf" highlighted with warning
    And message "Will be permanently deleted in 3 days"
```

---

## 6. Epic 4: User Access

### US-011: User Authentication

**Story**
```
Là một new employee,
Tôi muốn login vào hệ thống với credentials của tôi,
Để tôi có thể access Knowledge Bases mà tôi được phép.
```

| Attribute | Value |
|-----------|-------|
| **Priority** | P0 |
| **Story Points** | 3 |
| **Sprint** | MVP Sprint 1 |
| **FRS Reference** | FR-AU-001 to FR-AU-002 |

**Acceptance Criteria**:
```gherkin
Feature: Authentication

  Scenario: Successful login
    Given I am on the login page
    When I enter valid email "user@company.com"
    And I enter correct password
    And I click "Sign In"
    Then I should be redirected to Knowledge Base list
    And I should see my name in header

  Scenario: Invalid credentials
    Given I am on the login page
    When I enter wrong password
    And I click "Sign In"
    Then I should see error "Invalid email or password"
    And password field should be cleared
    And I should remain on login page

  Scenario: Account lockout
    Given I have entered wrong password 5 times
    When I try to login again
    Then I should see "Account temporarily locked. Try again in 15 minutes."
    And login should be blocked

  Scenario: Logout
    Given I am logged in
    When I click my profile icon
    And I click "Sign Out"
    Then I should be logged out
    And redirected to login page
    And trying to access any page should redirect to login
```

---

### US-012: Session Management

**Story**
```
Là một user working remotely,
Tôi muốn session được maintained securely,
Để tôi không phải login liên tục nhưng vẫn secure.
```

| Attribute | Value |
|-----------|-------|
| **Priority** | P0 |
| **Story Points** | 2 |
| **Sprint** | MVP Sprint 1 |
| **FRS Reference** | FR-AU-003 |

**Acceptance Criteria**:
```gherkin
Feature: Session Management

  Scenario: Session timeout warning
    Given I have been inactive for 7 hours 55 minutes
    When session is about to expire
    Then I should see warning "Your session will expire in 5 minutes"
    And I should have option to "Stay signed in"
    When I click "Stay signed in"
    Then session should be extended

  Scenario: Session expired
    Given my session has expired
    When I try to perform any action
    Then I should see "Session expired. Please sign in again."
    And I should be redirected to login page
    And my current URL should be saved for redirect after login

  Scenario: Multiple tabs
    Given I am logged in with multiple tabs open
    When I logout from one tab
    Then other tabs should detect this on next action
    And redirect to login page
```

---

## 7. User Journey Maps

### Journey 1: First-Time User - Creating First KB

```
┌────────────────────────────────────────────────────────────────────────────┐
│                    JOURNEY: First Knowledge Base Setup                      │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────┐    ┌─────────┐    ┌──────────┐    ┌────────┐    ┌────────────┐   │
│  │Login│───▶│Dashboard│───▶│Create KB │───▶│ Upload │───▶│First Query │   │
│  └─────┘    └─────────┘    └──────────┘    └────────┘    └────────────┘   │
│                                                                             │
│  Actions:                                                                   │
│  1. Login với credentials                                                   │
│  2. Thấy empty dashboard với "Create your first KB" CTA                    │
│  3. Click CTA, nhập tên và description                                      │
│  4. Được redirect tới KB page với upload prompt                            │
│  5. Drag & drop documents                                                   │
│  6. Đợi processing complete (xem progress)                                 │
│  7. Navigate to Query tab                                                   │
│  8. Ask first question, receive answer                                      │
│                                                                             │
│  Emotions:                                                                  │
│  😕 Uncertain ──▶ 🤔 Learning ──▶ ⏳ Waiting ──▶ 🎉 Success!                │
│                                                                             │
│  Pain Points to Address:                                                    │
│  • Không biết bắt đầu từ đâu → Clear onboarding CTA                        │
│  • Không chắc upload đúng file type → Show supported formats               │
│  • Không biết đợi bao lâu → Clear progress indicator                       │
│  • Không biết query gì → Suggest example questions                         │
│                                                                             │
│  Success Metrics:                                                           │
│  • Time from login to first query: < 15 minutes                            │
│  • Completion rate without support: > 90%                                   │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

### Journey 2: Daily User - Querying for Information

```
┌────────────────────────────────────────────────────────────────────────────┐
│                    JOURNEY: Daily Knowledge Query                           │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────┐    ┌─────────┐    ┌──────────┐    ┌────────┐    ┌────────────┐   │
│  │Login│───▶│Select KB│───▶│Ask Query │───▶│ Review │───▶│Take Action │   │
│  └─────┘    └─────────┘    └──────────┘    └────────┘    └────────────┘   │
│                                                                             │
│  User Goal: Quickly find answer to a specific question                     │
│                                                                             │
│  Optimal Flow:                                                              │
│  1. Login (or auto-login via session)                                      │
│  2. Click on most recently used KB (shown first)                           │
│  3. Go directly to Query tab (remember last tab)                           │
│  4. Type question                                                           │
│  5. Get answer with sources                                                 │
│  6. (Optional) Click source to verify                                       │
│  7. Copy answer or take action based on info                               │
│                                                                             │
│  Design Implications:                                                       │
│  • Recent KBs should be prominent                                           │
│  • Query tab should be default for returning users                         │
│  • Fast response time is critical                                           │
│  • Answer should be copy-able                                               │
│  • Consider bookmarks/favorites for frequent KBs                           │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Story Dependencies

```
US-001 (Create KB)
    │
    ├──▶ US-002 (Upload Docs) ──▶ US-004 (Monitor Processing)
    │         │
    │         └──▶ US-008 (Manage Docs) ──▶ US-010 (Trash)
    │
    ├──▶ US-003 (Configure Pipeline)
    │
    └──▶ US-009 (Update KB Settings)

US-002 (Upload) + US-003 (Config)
    │
    └──▶ US-005 (Ask Questions) ──▶ US-006 (View Sources)
              │
              └──▶ US-007 (Feedback)

US-011 (Auth) ──▶ ALL OTHER STORIES (prerequisite)
    │
    └──▶ US-012 (Session)
```

---

## 9. Sprint Planning Suggestion

### Sprint 1: Foundation
| Story | Points |
|-------|--------|
| US-011: Authentication | 3 |
| US-012: Session Management | 2 |
| US-001: Create KB | 3 |
| US-002: Upload Documents | 5 |
| US-004: Monitor Processing | 3 |
| **Total** | **16** |

### Sprint 2: Core Features
| Story | Points |
|-------|--------|
| US-003: Configure Pipeline | 8 |
| US-005: Ask Questions | 5 |
| US-006: View Sources | 3 |
| **Total** | **16** |

### Sprint 3: Management & Polish
| Story | Points |
|-------|--------|
| US-007: Feedback | 2 |
| US-008: Manage Documents | 5 |
| US-009: Update KB Settings | 2 |
| US-010: Trash & Recovery | 3 |
| **Total** | **12** |

---

## 10. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-02 | BA Team | Initial draft |
