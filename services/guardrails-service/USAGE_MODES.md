# Guardrails Service - Usage Modes

## 📌 Overview

Guardrails Service hỗ trợ **2 modes** khi tạo guardrails:

1. **Manual Mode** - User tự chọn template
2. **Auto Mode** - AI tự động chọn template tốt nhất

---

## 🎯 Mode 1: Manual Mode (User chọn template)

### Cách sử dụng:

User biết rõ mình cần template nào và tự chọn template_key.

### Request Format:

```json
{
  "user_id": "user123",
  "mode": "manual",
  "template_key": "content_safety",
  "user_context": "Customer support chatbot for e-commerce",
  "parameters": {
    "safety_level": "standard"
  },
  "metadata": {
    "department": "customer_service"
  }
}
```

### Required Fields (Manual Mode):
- ✅ `user_id` - User identifier
- ✅ `mode` - Must be "manual"
- ✅ `template_key` - Template to use (content_safety, pii_protection, etc.)
- ✅ `user_context` - Description of use case
- ⭕ `parameters` - Optional template-specific parameters
- ⭕ `metadata` - Optional additional info
- ❌ `instruction` - Ignored in manual mode

### Available Templates:

| Template Key | Purpose |
|--------------|---------|
| `content_safety` | Prevent harmful/inappropriate content |
| `pii_protection` | Protect personal information |
| `factual_accuracy` | Ensure accuracy, prevent hallucinations |
| `tone_control` | Control communication tone/style |
| `compliance` | Ensure regulatory compliance |

### Example Requests:

**Example 1: E-commerce Customer Support**
```bash
curl -X POST http://localhost:8083/api/v1/generations \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "ecommerce_co",
    "mode": "manual",
    "template_key": "tone_control",
    "user_context": "Customer support chatbot handling product inquiries and complaints",
    "parameters": {
      "tone": "friendly",
      "formality": "balanced",
      "audience": "customer"
    }
  }'
```

**Example 2: Healthcare Data Processing**
```bash
curl -X POST http://localhost:8083/api/v1/generations \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "healthtech_startup",
    "mode": "manual",
    "template_key": "pii_protection",
    "user_context": "Patient data processing system",
    "parameters": {
      "pii_types": ["names", "email_addresses", "phone_numbers", "addresses"],
      "redaction_strategy": "mask"
    },
    "metadata": {
      "compliance": "HIPAA"
    }
  }'
```

---

## 🤖 Mode 2: Auto Mode (AI chọn template)

### Cách sử dụng:

User không chắc chắn nên dùng template nào. AI sẽ phân tích context và instruction để tự động chọn template phù hợp nhất.

### Request Format:

```json
{
  "user_id": "user123",
  "mode": "auto",
  "user_context": "Healthcare chatbot handling patient medical records",
  "instruction": "Need to ensure HIPAA compliance and protect patient privacy",
  "parameters": {},
  "metadata": {
    "industry": "healthcare"
  }
}
```

### Required Fields (Auto Mode):
- ✅ `user_id` - User identifier
- ✅ `mode` - Must be "auto"
- ✅ `user_context` - Description of use case (IMPORTANT!)
- ⭕ `instruction` - Optional but recommended - detailed requirements
- ⭕ `parameters` - Optional (will be passed to selected template)
- ⭕ `metadata` - Optional additional info
- ❌ `template_key` - Ignored in auto mode

### How Auto Selection Works:

1. **AI analyzes** user_context + instruction
2. **Considers** all available templates
3. **Evaluates** based on:
   - Primary risk/concern
   - Data type being handled
   - Industry/domain
   - Regulatory requirements
   - Main goal (safety, compliance, quality, security)
4. **Selects** best matching template
5. **Returns** generated guardrail with selected template info in metadata

### Example Requests:

**Example 1: Healthcare Application**
```bash
curl -X POST http://localhost:8083/api/v1/generations \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "healthtech_startup",
    "mode": "auto",
    "user_context": "AI assistant helping patients schedule appointments and access their medical records",
    "instruction": "Must comply with HIPAA regulations and protect sensitive patient health information. Should prevent unauthorized access to medical data.",
    "parameters": {}
  }'
```

**AI sẽ chọn:** Có thể là `compliance` hoặc `pii_protection`

**Response includes:**
```json
{
  "id": "uuid-here",
  "template_key": "compliance",  // ← AI đã chọn
  "metadata": {
    "mode": "auto",
    "auto_selected": true,
    "selected_template_key": "compliance",
    "instruction": "Must comply with HIPAA..."
  }
}
```

---

**Example 2: Financial Advisory**
```bash
curl -X POST http://localhost:8083/api/v1/generations \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "fintech_platform",
    "mode": "auto",
    "user_context": "AI providing investment recommendations and portfolio analysis",
    "instruction": "Need to ensure accuracy of financial data, avoid giving misleading information, and include proper disclaimers about investment risks",
    "parameters": {}
  }'
```

**AI sẽ chọn:** Có thể là `factual_accuracy` hoặc `compliance`

---

**Example 3: Customer Service Bot**
```bash
curl -X POST http://localhost:8083/api/v1/generations \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "retail_company",
    "mode": "auto",
    "user_context": "Customer support chatbot for online retail, handling complaints, returns, and product questions",
    "instruction": "Should maintain friendly, helpful tone while staying professional. Need to handle angry customers empathetically.",
    "parameters": {}
  }'
```

**AI sẽ chọn:** Có thể là `tone_control`

---

**Example 4: Educational Platform**
```bash
curl -X POST http://localhost:8083/api/v1/generations \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "edtech_platform",
    "mode": "auto",
    "user_context": "AI tutor teaching mathematics and science to high school students",
    "instruction": "Must provide accurate information, cite sources when possible, and avoid giving students direct answers to homework. Should encourage learning.",
    "parameters": {}
  }'
```

**AI sẽ chọn:** Có thể là `factual_accuracy`

---

## 📊 Comparison: Manual vs Auto Mode

| Aspect | Manual Mode | Auto Mode |
|--------|-------------|-----------|
| **User knows template needed?** | ✅ Yes | ❌ No / Unsure |
| **template_key required?** | ✅ Yes | ❌ No (ignored) |
| **instruction field?** | Ignored | ⭕ Optional but recommended |
| **Selection process** | User decides | AI decides |
| **Speed** | Faster (no LLM call for selection) | Slightly slower (1 extra LLM call) |
| **Accuracy** | Depends on user knowledge | Depends on AI analysis |
| **Use case** | User is expert | User needs guidance |
| **Fallback** | Error if invalid template | Falls back to content_safety |

---

## 🔄 Mode Selection Guide

### Use **Manual Mode** when:
- ✅ You know exactly which guardrail you need
- ✅ You've explored templates and made a decision
- ✅ You want faster response time
- ✅ You're integrating programmatically with fixed template

### Use **Auto Mode** when:
- ✅ You're unsure which template fits best
- ✅ You want AI to analyze your requirements
- ✅ You have complex requirements spanning multiple areas
- ✅ You're prototyping and exploring options
- ✅ You want intelligent template recommendation

---

## 💡 Best Practices

### For Manual Mode:
1. **Explore templates first**: `GET /api/v1/templates`
2. **Preview before generating**: `POST /api/v1/templates/{key}/preview`
3. **Use compare endpoint**: Compare multiple templates to choose best one
4. **Provide clear user_context**: Helps with guardrail customization

### For Auto Mode:
1. **Write detailed user_context**: More context = better selection
2. **Include instruction field**: Explain your specific requirements
3. **Mention key concerns**:
   - Industry (healthcare, finance, etc.)
   - Regulations (HIPAA, GDPR, etc.)
   - Data types (PII, medical, financial)
   - Main goals (safety, accuracy, compliance)
4. **Check selected template**: Review metadata to see what AI chose
5. **Iterate if needed**: Adjust instruction and regenerate if selection isn't ideal

---

## 🎯 Auto Mode Tips for Better Selection

### Example: Good vs Bad Instructions

**❌ Bad (too vague):**
```json
{
  "user_context": "A chatbot",
  "instruction": "Make it safe"
}
```

**✅ Good (specific):**
```json
{
  "user_context": "Customer support chatbot for healthcare insurance company",
  "instruction": "Need to protect patient PHI data, comply with HIPAA, and maintain professional but empathetic tone when discussing sensitive medical topics"
}
```

### Keywords that Help AI Choose:

| Keywords | Likely Template |
|----------|-----------------|
| "GDPR", "HIPAA", "compliance", "regulatory" | `compliance` |
| "PII", "personal data", "privacy", "protect information" | `pii_protection` |
| "safe", "harmful", "inappropriate", "offensive" | `content_safety` |
| "accurate", "facts", "hallucination", "citations" | `factual_accuracy` |
| "tone", "style", "professional", "friendly", "communication" | `tone_control` |

---

## 📝 Response Format (Both Modes)

Both modes return the same response format:

```json
{
  "id": "uuid-here",
  "user_id": "user123",
  "template_key": "content_safety",  // Selected template
  "user_context": "...",
  "generated_guardrail": "# Content Safety Guardrail\n\n...",
  "parameters": {...},
  "metadata": {
    "mode": "auto",  // or "manual"
    "auto_selected": true,  // true for auto mode
    "selected_template_key": "content_safety",  // only in auto mode
    "instruction": "..."  // only if provided in auto mode
  },
  "created_at": "2024-01-19T..."
}
```

### Key Differences in Response:

**Manual Mode metadata:**
```json
{
  "mode": "manual",
  "auto_selected": false
}
```

**Auto Mode metadata:**
```json
{
  "mode": "auto",
  "auto_selected": true,
  "selected_template_key": "compliance",  // ← AI's choice
  "instruction": "Must comply with HIPAA..."  // ← Your instruction
}
```

---

## 🔍 Testing Auto Mode

You can test auto mode with different scenarios:

```bash
# Test 1: Healthcare scenario
curl -X POST http://localhost:8083/api/v1/generations \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "mode": "auto",
    "user_context": "Medical diagnosis assistant",
    "instruction": "Must comply with HIPAA and protect patient data"
  }'

# Expected: compliance or pii_protection

# Test 2: Content moderation scenario
curl -X POST http://localhost:8083/api/v1/generations \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "mode": "auto",
    "user_context": "Social media content moderation bot",
    "instruction": "Prevent hate speech, harassment, and harmful content"
  }'

# Expected: content_safety

# Test 3: Technical documentation scenario
curl -X POST http://localhost:8083/api/v1/generations \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "mode": "auto",
    "user_context": "Technical documentation AI writer",
    "instruction": "Must ensure accuracy, cite sources, avoid outdated information"
  }'

# Expected: factual_accuracy
```

---

## ⚙️ Fallback Behavior

If auto mode fails (LLM error, invalid selection, etc.), the service will:
1. Log the error
2. **Fallback to `content_safety`** template (safest default)
3. Continue processing normally
4. Include fallback info in metadata

This ensures the service never fails due to auto-selection issues.

---

## 🎓 Summary

- **Manual Mode**: You know → You choose → Faster
- **Auto Mode**: You describe → AI chooses → Smarter

Both modes produce the same guardrails, just different selection methods!

For most production use cases, **Manual Mode** is recommended once you've determined the right template.

For exploration, prototyping, or complex scenarios, **Auto Mode** provides intelligent assistance.
