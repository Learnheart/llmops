"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from app.main import app
    return TestClient(app)


@pytest.fixture
def sample_text():
    """Sample text for testing chunkers."""
    return """
    This is a sample document for testing the RAG service.
    It contains multiple paragraphs and sentences.

    The second paragraph discusses chunking strategies.
    Different chunking methods work better for different types of content.
    Recursive chunking tries to split at natural boundaries.

    The third paragraph is about embeddings.
    Embeddings convert text into dense vector representations.
    These vectors capture semantic meaning of the text.
    """


@pytest.fixture
def long_sample_text():
    """Longer sample text for testing chunk size limits."""
    paragraph = "This is a test sentence that will be repeated multiple times. "
    return paragraph * 100


@pytest.fixture
def sample_markdown():
    """Sample markdown content."""
    return b"""# Main Title

## Introduction

This is the introduction paragraph with some **bold** and *italic* text.

## Section One

Content of section one. It has multiple sentences.
This is the second sentence of section one.

### Subsection

A subsection with code:

```python
def hello():
    print("Hello World")
```

## Conclusion

Final thoughts and summary.
"""


@pytest.fixture
def sample_html():
    """Sample HTML content."""
    return b"""<!DOCTYPE html>
<html>
<head>
    <title>Test Document</title>
</head>
<body>
    <h1>Main Heading</h1>
    <p>First paragraph with some text content.</p>
    <h2>Second Heading</h2>
    <p>Second paragraph with more content.</p>
    <table>
        <tr><th>Name</th><th>Value</th></tr>
        <tr><td>Item 1</td><td>100</td></tr>
        <tr><td>Item 2</td><td>200</td></tr>
    </table>
</body>
</html>
"""


@pytest.fixture
def sample_csv():
    """Sample CSV content."""
    return b"""name,age,city
John,30,New York
Jane,25,Los Angeles
Bob,35,Chicago
"""


@pytest.fixture
def sample_text_file():
    """Sample plain text file content."""
    return b"""This is a plain text file.
It has multiple lines.
Each line contains some text.

There are also blank lines separating paragraphs.
This is useful for testing text parsing.
"""


@pytest.fixture
def ingestion_config():
    """Sample ingestion pipeline configuration."""
    return {
        "parser": {"type": "auto"},
        "chunker": {"type": "recursive", "chunk_size": 512, "chunk_overlap": 50},
        "embedder": {"type": "openai"},
        "indexer": {"type": "milvus"},
    }


@pytest.fixture
def retrieval_config():
    """Sample retrieval pipeline configuration."""
    return {
        "searcher": {"type": "hybrid", "semantic_weight": 0.7},
        "optimizers": [
            {"type": "score_threshold", "threshold": 0.5},
            {"type": "max_results", "limit": 5},
        ],
    }
