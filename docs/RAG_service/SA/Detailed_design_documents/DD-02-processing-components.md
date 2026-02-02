# Detailed Design — Processing Components Catalog

**Document ID:** DD-02
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
- [2. Content Extraction Group](#2-content-extraction-group)
  - [2.1 Parser Service](#21-parser-service)
  - [2.2 Content Router](#22-content-router)
- [3. Content Processing Group](#3-content-processing-group)
  - [3.1 Chunker Service](#31-chunker-service)
  - [3.2 Query Processor](#32-query-processor)
- [4. Embedding Group](#4-embedding-group)
  - [4.1 Embedder Service](#41-embedder-service)
- [5. Search & Ranking Group](#5-search--ranking-group)
  - [5.1 Searcher Service](#51-searcher-service)
  - [5.2 Reranker Service](#52-reranker-service)
- [6. Generation Group](#6-generation-group)
  - [6.1 LLM Service](#61-llm-service)
- [7. Indexer Service](#7-indexer-service)
- [8. Dependencies](#8-dependencies)

---

## 1. Overview

### Purpose

Document này mô tả chi tiết từng processing component được sử dụng trong Ingestion và Retrieval pipeline. Mỗi component được tổ chức như một "viên gạch" mà Pipeline Engine sử dụng để lắp ráp pipeline.

### Component Template

Mỗi component được mô tả theo cấu trúc:

| Section | Description |
|---------|-------------|
| **Purpose & Scope** | Component làm gì, ranh giới trách nhiệm |
| **Interface Definition** | Input/Output contract |
| **Internal Design** | Các strategy, thuật toán |
| **Configuration** | Tham số có thể cấu hình |
| **Error Handling** | Các loại lỗi và cách xử lý |
| **Dependencies** | Phụ thuộc vào component/service khác |

### Component Registry

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         COMPONENT REGISTRY                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  INGESTION PIPELINE COMPONENTS:                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Parser    │─▶│   Content   │─▶│   Chunker   │─▶│  Embedder   │─▶ Indexer  │
│  │   Service   │  │   Router    │  │   Service   │  │   Service   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                                  │
│  RETRIEVAL PIPELINE COMPONENTS:                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Query     │─▶│  Embedder   │─▶│  Searcher   │─▶│  Reranker   │─▶ LLM     │
│  │  Processor  │  │   Service   │  │   Service   │  │   Service   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Content Extraction Group

### 2.1 Parser Service

#### Purpose & Scope

Parser Service chịu trách nhiệm extract nội dung text từ các loại file khác nhau. Mỗi file type có một parser strategy riêng.

**In Scope:**
- Extract text content từ file
- Extract metadata (title, author, date, page count)
- Handle encoding issues

**Out of Scope:**
- Chunking (handled by Chunker Service)
- Content classification (handled by Content Router)

#### Interface Definition

```python
@dataclass
class ParserInput:
    file_path: str          # Path in MinIO
    file_type: str          # pdf, docx, xlsx, image, audio, html
    config: Dict[str, Any]  # Parser-specific configuration

@dataclass
class ParserOutput:
    text: str                    # Extracted text content
    metadata: Dict[str, Any]     # File metadata
    content_sections: List[ContentSection]  # Structured sections (optional)
    parse_info: ParseInfo        # Parsing stats

@dataclass
class ContentSection:
    content: str
    section_type: str  # text, table, image, code
    page_number: Optional[int]
    position: Optional[Tuple[int, int]]  # start_char, end_char
```

#### Internal Design - Parser Strategies

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         PARSER STRATEGIES                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  PDF Parser (pypdf / pdfplumber)                                        │    │
│  │                                                                          │    │
│  │  Strategy: pypdf (default)                                              │    │
│  │  • Fast text extraction                                                 │    │
│  │  • Handles most standard PDFs                                           │    │
│  │  • Limited table support                                                │    │
│  │                                                                          │    │
│  │  Strategy: pdfplumber (complex layouts)                                 │    │
│  │  • Better table extraction                                              │    │
│  │  • Position-aware text extraction                                       │    │
│  │  • Slower, more memory intensive                                        │    │
│  │                                                                          │    │
│  │  Strategy: marker (OCR fallback)                                        │    │
│  │  • For scanned PDFs                                                     │    │
│  │  • Uses OCR when text layer missing                                     │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  Document Parser (unstructured)                                          │    │
│  │                                                                          │    │
│  │  Supported: DOCX, DOC, RTF, ODT                                         │    │
│  │  • Preserves heading structure                                          │    │
│  │  • Extracts tables as markdown                                          │    │
│  │  • Handles embedded images (extract alt text)                           │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  Spreadsheet Parser (pandas)                                             │    │
│  │                                                                          │    │
│  │  Supported: XLSX, XLS, CSV                                              │    │
│  │  • Each sheet as separate section                                       │    │
│  │  • Header row detection                                                 │    │
│  │  • Output: JSON structure or markdown table                             │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  Image Parser (VLM)                                                      │    │
│  │                                                                          │    │
│  │  Strategy: vlm (Vision Language Model)                                  │    │
│  │  • GPT-4 Vision, Claude Vision                                          │    │
│  │  • Describe image content as text                                       │    │
│  │  • Extract text from diagrams/charts                                    │    │
│  │                                                                          │    │
│  │  Strategy: ocr (Tesseract/EasyOCR)                                      │    │
│  │  • For pure text images                                                 │    │
│  │  • Faster, cheaper than VLM                                             │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  Audio Parser (whisper)                                                  │    │
│  │                                                                          │    │
│  │  Supported: MP3, WAV, M4A, FLAC                                         │    │
│  │  • Whisper large-v3 for transcription                                   │    │
│  │  • Language detection                                                   │    │
│  │  • Speaker diarization (optional)                                       │    │
│  │  • Timestamps in metadata                                               │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  Code Parser (tree-sitter)                                               │    │
│  │                                                                          │    │
│  │  Supported: Python, JavaScript, TypeScript, Java, Go, Rust              │    │
│  │  • AST-based parsing                                                    │    │
│  │  • Extract functions, classes, imports                                  │    │
│  │  • Preserve code structure for semantic chunking                        │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  HTML Parser (beautifulsoup)                                             │    │
│  │                                                                          │    │
│  │  • Remove scripts, styles, navigation                                   │    │
│  │  • Extract main content area                                            │    │
│  │  • Preserve links as markdown                                           │    │
│  │  • Handle encoding issues                                               │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### Configuration

```json
{
  "parser": {
    "pdf": {
      "method": "pypdf",           // pypdf, pdfplumber, marker
      "lang": "Vietnamese",
      "ocr_fallback": true,
      "extract_tables": true,
      "output_format": "text"
    },
    "image": {
      "method": "vlm",             // vlm, ocr
      "llm_id": "gpt-4-vision",
      "max_tokens": 1000,
      "output_format": "text"
    },
    "audio": {
      "method": "whisper",
      "model_size": "large-v3",
      "language": "auto",
      "speaker_diarization": false,
      "output_format": "text"
    },
    "document": {
      "method": "unstructured",
      "preserve_structure": true,
      "output_format": "text"
    },
    "spreadsheet": {
      "method": "pandas",
      "header_row": "auto",
      "output_format": "json"       // json, markdown
    },
    "code": {
      "method": "treesitter",
      "language": "auto",
      "output_format": "ast"
    }
  }
}
```

#### Error Handling

| Error Type | Cause | Action |
|------------|-------|--------|
| `FileNotFoundError` | File missing from MinIO | Mark document ERROR, log |
| `UnsupportedFileType` | Unknown file extension | Mark document ERROR, log |
| `ParseError` | Parser library exception | Retry once, then ERROR |
| `EmptyContentError` | No text extracted | Mark document ERROR, log |
| `EncodingError` | Invalid character encoding | Auto-detect encoding, retry |
| `TimeoutError` | Parser took > 5 minutes | Kill process, mark ERROR |

### 2.2 Content Router

#### Purpose & Scope

Content Router phân tích nội dung đã extract và xác định loại content (text, table, code, mixed) để route đến chunker strategy phù hợp.

#### Interface Definition

```python
@dataclass
class RouterInput:
    text: str
    content_sections: List[ContentSection]
    file_type: str

@dataclass
class RouterOutput:
    content_type: str              # text, table, code, mixed
    sections: List[RoutedSection]
    routing_info: Dict[str, Any]

@dataclass
class RoutedSection:
    content: str
    content_type: str
    chunker_strategy: str          # recursive_semantic, row_group, ast_semantic
    position: Tuple[int, int]
```

#### Internal Design

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         CONTENT ROUTING LOGIC                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Input: Extracted content + metadata                                            │
│       │                                                                          │
│       ▼                                                                          │
│  ┌─────────────────┐                                                            │
│  │ File Type Check │                                                            │
│  └────────┬────────┘                                                            │
│           │                                                                      │
│      ┌────┴────────────────────────────────────────┐                            │
│      │                    │                         │                            │
│  Spreadsheet            Code                    Document/PDF                     │
│      │                    │                         │                            │
│      ▼                    ▼                         ▼                            │
│  table                  code                 ┌─────────────────┐                │
│  (row_group)         (ast_semantic)         │ Content Analysis │                │
│                                              └────────┬────────┘                │
│                                                       │                          │
│                                             ┌─────────┴─────────┐                │
│                                             │                   │                │
│                                        Has Tables?         Has Code?             │
│                                             │                   │                │
│                                        ┌────┴────┐         ┌────┴────┐          │
│                                        │         │         │         │          │
│                                       Yes       No        Yes       No          │
│                                        │         │         │         │          │
│                                        ▼         ▼         ▼         ▼          │
│                                      mixed     text      mixed     text         │
│                                                                                  │
│  Output: Content type + chunker strategy per section                            │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Content Detection Heuristics:**

```python
def detect_content_type(text: str) -> str:
    """Detect predominant content type in text."""

    # Table detection
    table_patterns = [
        r'\|.*\|.*\|',           # Markdown table
        r'\t.*\t.*\t',           # Tab-separated
        r'^\s*\d+\.\s+\w+\s+\d+', # Numbered list with values
    ]
    table_ratio = count_matches(text, table_patterns) / len(text.split('\n'))

    # Code detection
    code_patterns = [
        r'(def|class|function|const|let|var)\s+\w+',
        r'(import|from|require|include)\s+',
        r'\{[\s\S]*\}',
        r'(if|else|for|while|return)\s*[\(\{]',
    ]
    code_ratio = count_matches(text, code_patterns) / len(text.split('\n'))

    if table_ratio > 0.3:
        return 'table'
    elif code_ratio > 0.3:
        return 'code'
    elif table_ratio > 0.1 or code_ratio > 0.1:
        return 'mixed'
    else:
        return 'text'
```

---

## 3. Content Processing Group

### 3.1 Chunker Service

#### Purpose & Scope

Chunker Service chia content thành các chunks có kích thước phù hợp để embedding và retrieval. Mỗi content type có chunking strategy riêng.

#### Interface Definition

```python
@dataclass
class ChunkerInput:
    content: str
    content_type: str
    config: ChunkerConfig

@dataclass
class ChunkerOutput:
    chunks: List[Chunk]
    chunking_stats: ChunkingStats

@dataclass
class Chunk:
    id: str
    content: str
    index: int
    start_char: int
    end_char: int
    token_count: int
    metadata: Dict[str, Any]

@dataclass
class ChunkerConfig:
    method: str
    chunk_size: int = 512
    chunk_overlap: int = 50
    separators: List[str] = None
```

#### Internal Design - Chunking Strategies

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         CHUNKING STRATEGIES                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  STRATEGY 1: Recursive Semantic (for text)                              │    │
│  │                                                                          │    │
│  │  Algorithm:                                                              │    │
│  │  1. Split by largest separator (paragraph: \n\n)                        │    │
│  │  2. If chunk > max_size, recursively split by next separator            │    │
│  │  3. Merge small chunks until reaching target size                       │    │
│  │  4. Add overlap between chunks                                          │    │
│  │                                                                          │    │
│  │  Separators (priority order):                                           │    │
│  │  ["\n\n", "\n", ". ", ", ", " "]                                        │    │
│  │                                                                          │    │
│  │  Example:                                                                │    │
│  │  Input: "Paragraph 1...\n\nParagraph 2 is long...\n\nParagraph 3..."    │    │
│  │  Output: [Chunk1: P1, Chunk2: P2-part1, Chunk3: P2-part2+overlap, ...]  │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  STRATEGY 2: Row Group (for tables)                                     │    │
│  │                                                                          │    │
│  │  Algorithm:                                                              │    │
│  │  1. Parse table structure (header + rows)                               │    │
│  │  2. Group N rows per chunk (default: 20)                                │    │
│  │  3. Include header in every chunk                                       │    │
│  │  4. Add overlap rows between chunks                                     │    │
│  │                                                                          │    │
│  │  Example:                                                                │    │
│  │  Input: Table with 100 rows                                             │    │
│  │  Config: rows_per_chunk=20, overlap_rows=2                              │    │
│  │  Output: [                                                               │    │
│  │    Chunk1: Header + Row 1-20,                                           │    │
│  │    Chunk2: Header + Row 19-38,                                          │    │
│  │    Chunk3: Header + Row 37-56,                                          │    │
│  │    ...                                                                   │    │
│  │  ]                                                                       │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  STRATEGY 3: AST Semantic (for code)                                    │    │
│  │                                                                          │    │
│  │  Algorithm:                                                              │    │
│  │  1. Parse code into AST using tree-sitter                               │    │
│  │  2. Identify semantic units (functions, classes, methods)               │    │
│  │  3. Each unit becomes a chunk                                           │    │
│  │  4. Include relevant imports/context                                    │    │
│  │                                                                          │    │
│  │  Granularity options:                                                   │    │
│  │  • function: Each function as chunk                                     │    │
│  │  • class: Each class as chunk                                           │    │
│  │  • module: Entire file as chunk                                         │    │
│  │                                                                          │    │
│  │  Example:                                                                │    │
│  │  Input: Python file with 3 functions                                    │    │
│  │  Output: [                                                               │    │
│  │    Chunk1: imports + function1,                                         │    │
│  │    Chunk2: imports + function2,                                         │    │
│  │    Chunk3: imports + function3                                          │    │
│  │  ]                                                                       │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  STRATEGY 4: Adaptive (for mixed content)                               │    │
│  │                                                                          │    │
│  │  Algorithm:                                                              │    │
│  │  1. Detect content type for each section                                │    │
│  │  2. Apply appropriate strategy per section                              │    │
│  │  3. Maintain section boundaries                                         │    │
│  │                                                                          │    │
│  │  Example:                                                                │    │
│  │  Input: Document with text + table + code                               │    │
│  │  Output: [                                                               │    │
│  │    Chunks 1-3: text (recursive_semantic),                               │    │
│  │    Chunks 4-5: table (row_group),                                       │    │
│  │    Chunks 6-7: code (ast_semantic)                                      │    │
│  │  ]                                                                       │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### Configuration

```json
{
  "chunker": {
    "text": {
      "method": "recursive_semantic",
      "chunk_size": 512,
      "chunk_overlap": 50,
      "separators": ["\n\n", "\n", ". ", " "],
      "length_function": "token_count",
      "preserve_metadata": true
    },
    "table": {
      "method": "row_group",
      "rows_per_chunk": 20,
      "include_header": true,
      "overlap_rows": 2,
      "output_format": "markdown_table"
    },
    "code": {
      "method": "ast_semantic",
      "granularity": "function",
      "max_chunk_size": 1000,
      "include_context": true,
      "preserve_imports": true
    },
    "mixed": {
      "method": "adaptive",
      "detect_boundaries": true,
      "fallback": "text"
    }
  }
}
```

#### Error Handling

| Error Type | Cause | Action |
|------------|-------|--------|
| `EmptyContentError` | No content to chunk | Return empty list, log warning |
| `ChunkTooLargeError` | Single chunk exceeds limit | Force split at token boundary |
| `InvalidConfigError` | Invalid chunking parameters | Use defaults, log warning |

### 3.2 Query Processor

#### Purpose & Scope

Query Processor xử lý và tối ưu query trước khi search. Bao gồm query expansion, rewriting, và preprocessing.

#### Interface Definition

```python
@dataclass
class QueryProcessorInput:
    query: str
    config: QueryProcessConfig
    context: Optional[Dict[str, Any]] = None

@dataclass
class QueryProcessorOutput:
    original_query: str
    processed_query: str
    expanded_queries: List[str]
    processing_info: Dict[str, Any]

@dataclass
class QueryProcessConfig:
    enabled: bool = False
    methods: List[str] = field(default_factory=list)  # ["query_expansion", "query_rewrite"]
    expansion_count: int = 3
    llm_model: Optional[str] = None
```

#### Internal Design

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         QUERY PROCESSING METHODS                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  METHOD 1: Query Expansion                                               │    │
│  │                                                                          │    │
│  │  Generate multiple variations of the query to improve recall            │    │
│  │                                                                          │    │
│  │  Techniques:                                                             │    │
│  │  • Synonym expansion                                                     │    │
│  │  • LLM-based paraphrasing                                               │    │
│  │  • Acronym expansion                                                     │    │
│  │                                                                          │    │
│  │  Example:                                                                │    │
│  │  Input: "What is the ROI of project X?"                                 │    │
│  │  Output: [                                                               │    │
│  │    "What is the return on investment of project X?",                    │    │
│  │    "Project X profitability",                                           │    │
│  │    "Financial performance of project X"                                 │    │
│  │  ]                                                                       │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  METHOD 2: Query Rewrite                                                 │    │
│  │                                                                          │    │
│  │  Transform query for better semantic matching                           │    │
│  │                                                                          │    │
│  │  Techniques:                                                             │    │
│  │  • Remove filler words                                                   │    │
│  │  • Convert questions to statements                                      │    │
│  │  • Clarify ambiguous terms                                              │    │
│  │                                                                          │    │
│  │  Example:                                                                │    │
│  │  Input: "Can you tell me about the company's revenue?"                  │    │
│  │  Output: "Company revenue information and financial data"               │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  METHOD 3: HyDE (Hypothetical Document Embeddings)                       │    │
│  │                                                                          │    │
│  │  Generate a hypothetical answer, embed that instead of query            │    │
│  │                                                                          │    │
│  │  Algorithm:                                                              │    │
│  │  1. Use LLM to generate hypothetical answer to query                    │    │
│  │  2. Embed the hypothetical answer                                       │    │
│  │  3. Search for similar chunks                                           │    │
│  │                                                                          │    │
│  │  Example:                                                                │    │
│  │  Query: "What is the company vacation policy?"                          │    │
│  │  Hypothetical: "The company provides 15 days of paid vacation per       │    │
│  │                 year, with additional days for tenure..."               │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Embedding Group

### 4.1 Embedder Service

#### Purpose & Scope

Embedder Service chuyển đổi text thành dense vector representations. Sử dụng cho cả ingestion (embed chunks) và retrieval (embed query).

#### Interface Definition

```python
@dataclass
class EmbedderInput:
    texts: List[str]
    model: str
    batch_size: int = 100

@dataclass
class EmbedderOutput:
    embeddings: List[List[float]]
    model_info: ModelInfo
    usage: EmbeddingUsage

@dataclass
class ModelInfo:
    model_name: str
    dimension: int
    max_tokens: int

@dataclass
class EmbeddingUsage:
    total_tokens: int
    latency_ms: int
```

#### Internal Design

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         EMBEDDING MODELS                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  Text Embeddings                                                         │    │
│  │                                                                          │    │
│  │  Model: jina-embeddings-v3                                              │    │
│  │  • Dimension: 1024 (default), up to 3072                                │    │
│  │  • Max tokens: 8192                                                     │    │
│  │  • Multilingual support (Vietnamese)                                    │    │
│  │  • Task-specific: retrieval.query, retrieval.passage                    │    │
│  │                                                                          │    │
│  │  Model: text-embedding-3-large (OpenAI)                                 │    │
│  │  • Dimension: 3072 (configurable)                                       │    │
│  │  • Max tokens: 8191                                                     │    │
│  │                                                                          │    │
│  │  Model: embed-multilingual-v3.0 (Cohere)                                │    │
│  │  • Dimension: 1024                                                      │    │
│  │  • Good for multilingual, including Vietnamese                          │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  Code Embeddings                                                         │    │
│  │                                                                          │    │
│  │  Model: voyage-code-2                                                   │    │
│  │  • Optimized for code understanding                                     │    │
│  │  • Better semantic similarity for code                                  │    │
│  │  • Dimension: 1536                                                      │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### Batching Strategy

```python
async def embed_chunks(chunks: List[str], config: EmbedderConfig) -> List[List[float]]:
    """Embed chunks with batching for efficiency."""

    embeddings = []
    batch_size = config.batch_size

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]

        # Call embedding API
        batch_embeddings = await call_embedding_api(
            texts=batch,
            model=config.model,
            base_url=config.base_url
        )

        embeddings.extend(batch_embeddings)

        # Rate limiting
        if config.rate_limit:
            await asyncio.sleep(config.rate_limit_delay)

    return embeddings
```

#### Caching

```python
class EmbeddingCache:
    """Cache embeddings to avoid redundant API calls."""

    def __init__(self, redis_client, ttl_days: int = 7):
        self.redis = redis_client
        self.ttl = ttl_days * 86400

    def get_cache_key(self, text: str, model: str) -> str:
        text_hash = hashlib.md5(text.encode()).hexdigest()
        return f"cache:embed:{model}:{text_hash}"

    async def get(self, text: str, model: str) -> Optional[List[float]]:
        key = self.get_cache_key(text, model)
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)
        return None

    async def set(self, text: str, model: str, embedding: List[float]):
        key = self.get_cache_key(text, model)
        await self.redis.setex(key, self.ttl, json.dumps(embedding))
```

#### Error Handling

| Error Type | Cause | Action |
|------------|-------|--------|
| `RateLimitError` | API rate limit exceeded | Exponential backoff, retry |
| `TokenLimitError` | Text exceeds max tokens | Truncate text, log warning |
| `ModelNotFoundError` | Invalid model name | Fail with error |
| `APITimeoutError` | Embedding API timeout | Retry 3 times, then fail |

---

## 5. Search & Ranking Group

### 5.1 Searcher Service

#### Purpose & Scope

Searcher Service thực hiện hybrid search kết hợp vector similarity (Milvus) và keyword matching (Elasticsearch), với RRF fusion.

#### Interface Definition

```python
@dataclass
class SearcherInput:
    query_vector: List[float]
    query_text: str
    kb_id: str
    user_context: UserContext
    config: SearchConfig

@dataclass
class SearcherOutput:
    results: List[SearchResult]
    search_info: SearchInfo

@dataclass
class SearchResult:
    chunk_id: str
    document_id: str
    content: str
    score: float
    vector_score: Optional[float]
    keyword_score: Optional[float]
    metadata: Dict[str, Any]

@dataclass
class SearchConfig:
    type: str  # semantic, keyword, hybrid
    top_k: int = 10
    similarity_threshold: float = 0.2
    vector_weight: float = 0.6
    keyword_weight: float = 0.4
    fusion_method: str = "rrf"
```

#### Internal Design

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         HYBRID SEARCH FLOW                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Query + Query Vector                                                            │
│       │                                                                          │
│       ├───────────────────────────────────────┐                                  │
│       │                                       │                                  │
│       ▼                                       ▼                                  │
│  ┌─────────────────┐                  ┌─────────────────┐                       │
│  │  Milvus Search  │                  │   ES Search     │                       │
│  │                 │                  │                 │                       │
│  │  • Vector       │                  │  • BM25         │                       │
│  │    similarity   │                  │  • Fulltext     │                       │
│  │  • COSINE       │                  │  • Analyzer     │                       │
│  │  • top_k * 2    │                  │  • top_k * 2    │                       │
│  │  • Permission   │                  │  • Permission   │                       │
│  │    filter       │                  │    filter       │                       │
│  └────────┬────────┘                  └────────┬────────┘                       │
│           │                                    │                                │
│           ▼                                    ▼                                │
│  Results A (vector scores)           Results B (BM25 scores)                    │
│           │                                    │                                │
│           └──────────────┬─────────────────────┘                                │
│                          │                                                       │
│                          ▼                                                       │
│                  ┌───────────────────┐                                          │
│                  │   RRF Fusion      │                                          │
│                  │                   │                                          │
│                  │  score = Σ 1/(k+rank_i)                                      │
│                  │  k = 60 (constant)│                                          │
│                  │                   │                                          │
│                  │  Combine ranks    │                                          │
│                  │  from both sources│                                          │
│                  └─────────┬─────────┘                                          │
│                            │                                                     │
│                            ▼                                                     │
│                    Final Results (top_k)                                        │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### Permission Filter Implementation

```python
def build_permission_filter(user_context: UserContext, kb_id: str) -> str:
    """Build Milvus filter expression for permission check."""

    user_id = user_context.user_id
    group_ids = user_context.group_ids

    # Base filter: active chunks in KB
    filters = [
        f"kb_id == '{kb_id}'",
        "is_active == true",
    ]

    # Permission filter
    permission_filter = (
        f"(permission_type == 'inherit' or "
        f"(permission_type == 'private' and owner_id == '{user_id}') or "
        f"(is_public == true) or "
        f"('{user_id}' in allowed_user_ids)"
    )

    # Add group check if user has groups
    if group_ids:
        group_list = str(group_ids)
        permission_filter += f" or (any(g in allowed_group_ids for g in {group_list}))"

    permission_filter += ")"
    filters.append(permission_filter)

    return " and ".join(filters)
```

#### RRF (Reciprocal Rank Fusion) Algorithm

```python
def rrf_fusion(
    vector_results: List[SearchResult],
    keyword_results: List[SearchResult],
    k: int = 60
) -> List[SearchResult]:
    """Fuse results from vector and keyword search using RRF."""

    # Build rank maps
    vector_ranks = {r.chunk_id: i + 1 for i, r in enumerate(vector_results)}
    keyword_ranks = {r.chunk_id: i + 1 for i, r in enumerate(keyword_results)}

    # Collect all unique chunk IDs
    all_chunk_ids = set(vector_ranks.keys()) | set(keyword_ranks.keys())

    # Calculate RRF scores
    rrf_scores = {}
    for chunk_id in all_chunk_ids:
        score = 0
        if chunk_id in vector_ranks:
            score += 1.0 / (k + vector_ranks[chunk_id])
        if chunk_id in keyword_ranks:
            score += 1.0 / (k + keyword_ranks[chunk_id])
        rrf_scores[chunk_id] = score

    # Sort by RRF score
    sorted_chunks = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

    # Build final results
    chunk_map = {r.chunk_id: r for r in vector_results + keyword_results}
    results = []
    for chunk_id, rrf_score in sorted_chunks:
        result = chunk_map[chunk_id]
        result.score = rrf_score
        result.vector_score = vector_ranks.get(chunk_id)
        result.keyword_score = keyword_ranks.get(chunk_id)
        results.append(result)

    return results
```

### 5.2 Reranker Service

#### Purpose & Scope

Reranker Service re-order search results sử dụng cross-encoder model để đạt độ chính xác cao hơn bi-encoder (embedding).

#### Interface Definition

```python
@dataclass
class RerankerInput:
    query: str
    results: List[SearchResult]
    config: RerankerConfig

@dataclass
class RerankerOutput:
    reranked_results: List[SearchResult]
    reranking_info: RerankingInfo

@dataclass
class RerankerConfig:
    enabled: bool = False
    model: str = "bge-reranker-v2-m3"
    base_url: str = None
    top_k: int = 5
    min_score: float = 0.0
```

#### Internal Design

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         RERANKING FLOW                                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Search Results (N items)                                                        │
│       │                                                                          │
│       ▼                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  Cross-Encoder Scoring                                                   │    │
│  │                                                                          │    │
│  │  For each result:                                                       │    │
│  │    input = [query, result.content]                                      │    │
│  │    score = cross_encoder(input)                                         │    │
│  │                                                                          │    │
│  │  Cross-encoder considers:                                               │    │
│  │  • Full interaction between query and document                          │    │
│  │  • Semantic similarity at token level                                   │    │
│  │  • Contextual relevance                                                 │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│       │                                                                          │
│       ▼                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  Score Normalization & Filtering                                        │    │
│  │                                                                          │    │
│  │  • Normalize scores to [0, 1]                                           │    │
│  │  • Filter by min_score threshold                                        │    │
│  │  • Sort by reranker score                                               │    │
│  │  • Keep top_k results                                                   │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│       │                                                                          │
│       ▼                                                                          │
│  Reranked Results (top_k items)                                                  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### Supported Reranker Models

| Model | Dimension | Languages | Performance |
|-------|-----------|-----------|-------------|
| bge-reranker-v2-m3 | - | Multilingual | High accuracy, moderate speed |
| cohere-rerank-v3 | - | Multilingual | Very high accuracy, API-based |
| jina-reranker-v1 | - | Multilingual | Good balance |

---

## 6. Generation Group

### 6.1 LLM Service

#### Purpose & Scope

LLM Service sinh câu trả lời từ context (retrieved chunks) và query sử dụng Large Language Model.

#### Interface Definition

```python
@dataclass
class LLMInput:
    query: str
    context_chunks: List[Chunk]
    config: LLMConfig
    chat_history: Optional[List[Message]] = None

@dataclass
class LLMOutput:
    answer: str
    source_chunks: List[str]  # chunk IDs used
    usage: LLMUsage
    metadata: Dict[str, Any]

@dataclass
class LLMConfig:
    model: str = "gpt-4"
    base_url: str = None
    temperature: float = 0.7
    max_tokens: int = 2048
    stream: bool = False
```

#### Internal Design

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         LLM SERVICE FLOW                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Query + Context Chunks                                                          │
│       │                                                                          │
│       ▼                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  Prompt Construction                                                     │    │
│  │                                                                          │    │
│  │  System Prompt:                                                          │    │
│  │  "You are a helpful assistant. Answer questions based on the            │    │
│  │   provided context. If the answer is not in the context, say so.        │    │
│  │   Always cite your sources using [Source N] format."                    │    │
│  │                                                                          │    │
│  │  Context:                                                                │    │
│  │  [Source 1]: {chunk_1.content}                                          │    │
│  │  [Source 2]: {chunk_2.content}                                          │    │
│  │  ...                                                                     │    │
│  │                                                                          │    │
│  │  User Query: {query}                                                    │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│       │                                                                          │
│       ▼                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  Context Window Management                                               │    │
│  │                                                                          │    │
│  │  1. Calculate available tokens:                                         │    │
│  │     available = model_max_tokens - system_prompt - response_reserve     │    │
│  │                                                                          │    │
│  │  2. Truncate context if needed:                                         │    │
│  │     • Prioritize chunks by rerank score                                 │    │
│  │     • Include as many chunks as fit                                     │    │
│  │     • Log warning if truncation occurs                                  │    │
│  │                                                                          │    │
│  │  3. Token budget:                                                       │    │
│  │     • System prompt: ~500 tokens                                        │    │
│  │     • Context: ~3000 tokens (adjustable)                                │    │
│  │     • Response reserve: ~2000 tokens                                    │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│       │                                                                          │
│       ▼                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  LLM API Call                                                            │    │
│  │                                                                          │    │
│  │  if config.stream:                                                      │    │
│  │      yield tokens as they arrive                                        │    │
│  │  else:                                                                  │    │
│  │      return complete response                                           │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│       │                                                                          │
│       ▼                                                                          │
│  Answer + Source References                                                      │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### Prompt Template

```python
SYSTEM_PROMPT = """You are a knowledgeable assistant for {kb_name}.

Instructions:
1. Answer questions based ONLY on the provided context
2. If the answer is not in the context, clearly state that
3. Cite sources using [Source N] format when referencing specific information
4. Be concise but comprehensive
5. Use the same language as the user's question

Context:
{context}

Remember: Only use information from the context above. Do not make up information."""

def build_context(chunks: List[Chunk], max_tokens: int) -> str:
    """Build context string from chunks within token limit."""

    context_parts = []
    current_tokens = 0

    for i, chunk in enumerate(chunks, 1):
        chunk_text = f"[Source {i}]: {chunk.content}\n"
        chunk_tokens = count_tokens(chunk_text)

        if current_tokens + chunk_tokens > max_tokens:
            break

        context_parts.append(chunk_text)
        current_tokens += chunk_tokens

    return "\n".join(context_parts)
```

---

## 7. Indexer Service

#### Purpose & Scope

Indexer Service lưu chunks và vectors vào Milvus (vector search) và Elasticsearch (fulltext search).

#### Interface Definition

```python
@dataclass
class IndexerInput:
    chunks: List[Chunk]
    vectors: List[List[float]]
    document_id: str
    kb_id: str
    user_context: UserContext
    config: IndexerConfig

@dataclass
class IndexerOutput:
    indexed_count: int
    milvus_ids: List[str]
    es_ids: List[str]
    indexing_info: IndexingInfo

@dataclass
class IndexerConfig:
    target_milvus: bool = True
    target_elasticsearch: bool = True
    batch_size: int = 100
```

#### Internal Design

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         INDEXING FLOW                                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Chunks + Vectors                                                                │
│       │                                                                          │
│       ├───────────────────────────────────────┐                                  │
│       │                                       │                                  │
│       ▼                                       ▼                                  │
│  ┌─────────────────┐                  ┌─────────────────┐                       │
│  │  Milvus Insert  │                  │   ES Index      │                       │
│  │                 │                  │                 │                       │
│  │  Data:          │                  │  Data:          │                       │
│  │  • chunk_id     │                  │  • chunk_id     │                       │
│  │  • document_id  │                  │  • document_id  │                       │
│  │  • embedding    │                  │  • content      │                       │
│  │  • is_active    │                  │  • is_active    │                       │
│  │  • permission_  │                  │  • permission_  │                       │
│  │    type         │                  │    type         │                       │
│  │  • owner_id     │                  │  • owner_id     │                       │
│  │  • is_public    │                  │  • allowed_*    │                       │
│  │  • content_type │                  │  • metadata     │                       │
│  └────────┬────────┘                  └────────┬────────┘                       │
│           │                                    │                                │
│           ▼                                    ▼                                │
│  ┌─────────────────┐                  ┌─────────────────┐                       │
│  │  Save chunk     │                  │  Bulk index     │                       │
│  │  metadata to    │                  │  to ES          │                       │
│  │  PostgreSQL     │                  │                 │                       │
│  └─────────────────┘                  └─────────────────┘                       │
│                                                                                  │
│  Parallel Execution:                                                             │
│  • Milvus insert and ES index run in parallel                                   │
│  • PostgreSQL update is synchronous (for consistency)                           │
│  • Rollback if any fails                                                        │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### Batch Processing

```python
async def index_chunks(
    chunks: List[Chunk],
    vectors: List[List[float]],
    config: IndexerConfig
) -> IndexerOutput:
    """Index chunks to Milvus and Elasticsearch in batches."""

    batch_size = config.batch_size
    milvus_ids = []
    es_ids = []

    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i + batch_size]
        batch_vectors = vectors[i:i + batch_size]

        # Parallel insert
        milvus_task = insert_to_milvus(batch_chunks, batch_vectors)
        es_task = insert_to_elasticsearch(batch_chunks)

        batch_milvus_ids, batch_es_ids = await asyncio.gather(
            milvus_task,
            es_task
        )

        milvus_ids.extend(batch_milvus_ids)
        es_ids.extend(batch_es_ids)

    # Update PostgreSQL
    await update_chunk_references(chunks, milvus_ids, es_ids)

    return IndexerOutput(
        indexed_count=len(chunks),
        milvus_ids=milvus_ids,
        es_ids=es_ids
    )
```

---

## 8. Dependencies

### Component Dependencies

| Component | Depends On | External Services |
|-----------|-----------|-------------------|
| Parser | MinIO (file storage) | VLM API (for images), Whisper API (for audio) |
| Content Router | Parser output | - |
| Chunker | Content Router output | - |
| Embedder | Chunker output, Query Processor output | Embedding API |
| Indexer | Embedder output | Milvus, Elasticsearch |
| Searcher | Embedder output (query vector) | Milvus, Elasticsearch |
| Reranker | Searcher output | Reranker API |
| LLM | Searcher/Reranker output | LLM API |
| Query Processor | - | LLM API (optional) |

### Cross-Document References

| Reference | Document | Section |
|-----------|----------|---------|
| Pipeline orchestration | [DD-01-pipeline-engine.md] | Section 4: Pipeline Executor |
| Factory registration | [DD-01-pipeline-engine.md] | Section 3: Pipeline Builder |
| Database schema for chunks | [DD-04-data-architecture.md] | Section 2.2: RAG Data Tables |
| Permission filtering | [DD-05-data-governance.md] | Section 1.4: Query-Time Permission Filter |
| Caching strategies | [DD-04-data-architecture.md] | Section 6: Redis Caching |

---

*Document Version: 1.0*
*Last Updated: 2026-02-02*
