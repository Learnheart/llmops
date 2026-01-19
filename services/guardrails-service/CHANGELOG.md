# Changelog - Guardrails Service

## [0.2.1] - 2024-01-19

### 🔧 Fixed - Versioning (Insert-Only Principle)

**Critical Fix: Variants now follow insert-only versioning**

Previously, variants could be updated in place, which violated immutability principles. This has been corrected:

#### Changes:

1. **API Endpoint Change**
   - **Removed**: `PUT /api/v1/variants/{id}`
   - **Added**: `POST /api/v1/variants/{id}/versions`
   - New endpoint creates a new variant record instead of updating

2. **Service Layer**
   - Replaced `update_variant()` with `create_new_version()`
   - New method:
     - Fetches source variant
     - Increments version number
     - **Creates new variant record** (INSERT)
     - **Does NOT modify** source variant
     - Logs change in history

3. **Schema Updates**
   - Removed `increment_version` field from `UpdateVariantRequest`
   - Updated docstring to clarify insert-only behavior
   - Removed `category` field from `TemplateInfo` (flattened templates)

4. **Documentation Updates**
   - Updated ARCHITECTURE.md with new flow diagram
   - Updated SUMMARY.md with insert-only explanation
   - Updated README.md examples
   - Marked repository's `update()` method as DEPRECATED

#### Benefits:

- **Immutability**: Old versions never change (audit-safe)
- **Full History**: Every version is preserved in database
- **Rollback**: Can reference any previous version
- **Compliance**: Meets regulatory audit requirements

#### Migration Notes:

**Old API call (deprecated):**
```bash
PUT /api/v1/variants/{id}
{
  "user_id": "user123",
  "guardrail_content": "Updated content",
  "increment_version": true
}
```

**New API call:**
```bash
POST /api/v1/variants/{id}/versions
{
  "user_id": "user123",
  "guardrail_content": "Updated content"
}
```

---

## [0.2.0] - 2024-01-19

### ✨ Added - Dual Mode Support

**Major Feature: Auto Template Selection**

The service now supports 2 modes for generating guardrails:

#### 1. Manual Mode (Original)
- User selects template explicitly via `template_key`
- Direct control over which guardrail template to use
- Faster (no additional LLM call)

#### 2. Auto Mode (NEW)
- AI automatically selects the best template based on context
- User provides `user_context` + optional `instruction`
- LLM analyzes requirements and chooses optimal template
- Falls back to `content_safety` if selection fails

### 📝 Changes

#### Modified Files:

1. **app/models/schemas.py**
   - Added `mode` field to `GenerateGuardrailRequest` (default: "manual")
   - Made `template_key` optional (required only in manual mode)
   - Added `instruction` field for auto mode
   - Added `model_validator` to validate mode-specific requirements

2. **app/services/guardrail_service.py**
   - Added `LLMService` import and initialization
   - Added `_auto_select_template()` method:
     - Uses LLM to analyze context and instruction
     - Evaluates all available templates
     - Returns best matching template key
     - Includes fallback to `content_safety`
   - Updated `generate_guardrail()` method:
     - Supports both manual and auto modes
     - Routes to appropriate selection logic
     - Stores mode info in metadata

3. **README.md**
   - Added section about dual mode support
   - Updated examples for both modes
   - Added reference to USAGE_MODES.md

#### New Files:

4. **USAGE_MODES.md** (NEW)
   - Comprehensive guide for both modes
   - When to use each mode
   - Best practices and examples
   - Auto mode tips for better selection
   - Comparison table

5. **CHANGELOG.md** (NEW - this file)
   - Track version changes

### 🎯 Usage Examples

**Manual Mode (Original behavior):**
```json
{
  "user_id": "user123",
  "mode": "manual",
  "template_key": "content_safety",
  "user_context": "Customer chatbot",
  "parameters": {"safety_level": "standard"}
}
```

**Auto Mode (New feature):**
```json
{
  "user_id": "user123",
  "mode": "auto",
  "user_context": "Healthcare chatbot handling patient records",
  "instruction": "Need HIPAA compliance and protect patient privacy",
  "parameters": {}
}
```

### 🔄 Response Changes

Responses now include mode information in metadata:

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
  "selected_template_key": "compliance",
  "instruction": "Need HIPAA compliance..."
}
```

### ⚙️ Technical Details

**Auto Selection Algorithm:**
1. Fetch all available templates with descriptions
2. Build selection prompt with:
   - Template descriptions and categories
   - User context
   - User instruction (if provided)
   - Selection criteria
3. Call LLM with low temperature (0.3) for consistent results
4. Validate selected template key
5. Fallback to `content_safety` if invalid/error

**Fallback Strategy:**
- Invalid template key → `content_safety`
- LLM call fails → `content_safety`
- Any error → `content_safety` + log error

### 🎓 Benefits

1. **Flexibility**: Users can choose their preferred approach
2. **Intelligence**: AI helps users who are unsure which template to use
3. **Simplicity**: Auto mode reduces decision overhead
4. **Safety**: Fallback ensures service always works
5. **Backward Compatible**: Default mode is "manual" (original behavior)

### 📊 Performance Impact

- **Manual Mode**: No change (same performance)
- **Auto Mode**: +1 LLM call for template selection (~1-2 seconds)

### 🔒 Backward Compatibility

✅ **Fully backward compatible**

Existing requests without `mode` field will default to "manual" mode and work exactly as before.

```json
// Old format still works
{
  "user_id": "user123",
  "template_key": "content_safety",
  "user_context": "Customer chatbot"
}
// Treated as mode="manual"
```

### 📚 Documentation

- **USAGE_MODES.md**: Complete guide for both modes
- **README.md**: Updated with dual mode examples
- **ARCHITECTURE.md**: (To be updated with auto-selection flow)

---

## [0.1.0] - 2024-01-19

### Initial Release

- 5 Guardrail templates (content_safety, pii_protection, factual_accuracy, tone_control, compliance)
- Template registry with Factory pattern
- Guardrail generation with versioning
- Variant management with history tracking
- RESTful API with FastAPI
- PostgreSQL database with AsyncPG
- Multi-provider LLM support (Groq, OpenAI, Anthropic)
- Health check endpoints
- Docker support
- Comprehensive documentation

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 0.2.1 | 2024-01-19 | Fixed versioning to follow insert-only principle |
| 0.2.0 | 2024-01-19 | Added auto template selection mode |
| 0.1.0 | 2024-01-19 | Initial release |
