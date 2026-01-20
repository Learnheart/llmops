"""Tests for parser components."""

import pytest


class TestTextParser:
    """Tests for TextParser."""

    @pytest.fixture
    def parser(self):
        from app.components.parsers import TextParser
        return TextParser()

    @pytest.mark.asyncio
    async def test_parse_text_file(self, parser, sample_text_file):
        """Test parsing plain text file."""
        result = await parser.parse(sample_text_file, "test.txt")

        assert result.content is not None
        assert len(result.content) > 0
        assert "plain text file" in result.content
        assert result.metadata["filename"] == "test.txt"

    @pytest.mark.asyncio
    async def test_parse_with_encoding(self, parser):
        """Test parsing with specific encoding."""
        content = "Hello World".encode("utf-8")
        result = await parser.parse(content, "test.txt", encoding="utf-8")

        assert result.content == "Hello World"

    @pytest.mark.asyncio
    async def test_parse_empty_file(self, parser):
        """Test parsing empty file."""
        result = await parser.parse(b"", "empty.txt")

        assert result.content == ""

    def test_supported_extensions(self, parser):
        """Test supported extensions."""
        assert parser.supports_extension("txt")
        assert parser.supports_extension(".txt")
        assert parser.supports_extension("text")
        assert not parser.supports_extension("pdf")


class TestMarkdownParser:
    """Tests for MarkdownParser."""

    @pytest.fixture
    def parser(self):
        from app.components.parsers import MarkdownParser
        return MarkdownParser()

    @pytest.mark.asyncio
    async def test_parse_markdown(self, parser, sample_markdown):
        """Test parsing markdown file."""
        result = await parser.parse(sample_markdown, "test.md")

        assert result.content is not None
        assert "Main Title" in result.content
        assert "Introduction" in result.content
        assert result.metadata["format"] == "markdown"

    @pytest.mark.asyncio
    async def test_extract_headers(self, parser, sample_markdown):
        """Test header extraction."""
        result = await parser.parse(sample_markdown, "test.md")

        assert "headers" in result.metadata
        headers = result.metadata["headers"]
        assert len(headers) > 0
        assert headers[0]["level"] == 1
        assert headers[0]["title"] == "Main Title"

    @pytest.mark.asyncio
    async def test_extract_title(self, parser, sample_markdown):
        """Test title extraction from first heading."""
        result = await parser.parse(sample_markdown, "test.md")

        assert result.metadata.get("title") == "Main Title"

    def test_supported_extensions(self, parser):
        """Test supported extensions."""
        assert parser.supports_extension("md")
        assert parser.supports_extension("markdown")
        assert not parser.supports_extension("txt")


class TestHTMLParser:
    """Tests for HTMLParser."""

    @pytest.fixture
    def parser(self):
        from app.components.parsers import HTMLParser
        return HTMLParser()

    @pytest.mark.asyncio
    async def test_parse_html(self, parser, sample_html):
        """Test parsing HTML file."""
        result = await parser.parse(sample_html, "test.html")

        assert result.content is not None
        assert "Main Heading" in result.content
        assert "First paragraph" in result.content
        assert result.metadata["format"] == "html"

    @pytest.mark.asyncio
    async def test_extract_title(self, parser, sample_html):
        """Test title extraction."""
        result = await parser.parse(sample_html, "test.html")

        assert result.metadata.get("title") == "Test Document"

    @pytest.mark.asyncio
    async def test_extract_headings(self, parser, sample_html):
        """Test heading extraction."""
        result = await parser.parse(sample_html, "test.html")

        assert "headings" in result.metadata
        headings = result.metadata["headings"]
        assert len(headings) >= 2

    @pytest.mark.asyncio
    async def test_extract_tables(self, parser, sample_html):
        """Test table extraction."""
        result = await parser.parse(sample_html, "test.html", extract_tables=True)

        assert result.tables is not None
        assert len(result.tables) > 0

    def test_supported_extensions(self, parser):
        """Test supported extensions."""
        assert parser.supports_extension("html")
        assert parser.supports_extension("htm")
        assert not parser.supports_extension("md")


class TestCSVParser:
    """Tests for CSVParser."""

    @pytest.fixture
    def parser(self):
        from app.components.parsers import CSVParser
        return CSVParser()

    @pytest.mark.asyncio
    async def test_parse_csv(self, parser, sample_csv):
        """Test parsing CSV file."""
        result = await parser.parse(sample_csv, "test.csv")

        assert result.content is not None
        assert "John" in result.content
        assert "New York" in result.content
        assert result.metadata["format"] == "csv"

    @pytest.mark.asyncio
    async def test_extract_columns(self, parser, sample_csv):
        """Test column extraction."""
        result = await parser.parse(sample_csv, "test.csv")

        assert "columns" in result.metadata
        assert result.metadata["columns"] == ["name", "age", "city"]

    @pytest.mark.asyncio
    async def test_row_count(self, parser, sample_csv):
        """Test row count."""
        result = await parser.parse(sample_csv, "test.csv")

        assert result.metadata["row_count"] == 3  # Excluding header

    @pytest.mark.asyncio
    async def test_table_output(self, parser, sample_csv):
        """Test tables in output."""
        result = await parser.parse(sample_csv, "test.csv")

        assert result.tables is not None
        assert len(result.tables) == 1
        assert result.tables[0]["rows"] == 3

    def test_supported_extensions(self, parser):
        """Test supported extensions."""
        assert parser.supports_extension("csv")
        assert parser.supports_extension("tsv")
        assert not parser.supports_extension("xlsx")


class TestAutoParser:
    """Tests for AutoParser (auto-detection)."""

    @pytest.fixture
    def parser(self):
        from app.components.parsers import AutoParser
        return AutoParser()

    @pytest.mark.asyncio
    async def test_detect_text(self, parser, sample_text_file):
        """Test auto-detection for text files."""
        result = await parser.parse(sample_text_file, "document.txt")

        assert result.content is not None
        assert result.metadata.get("auto_detected") is True

    @pytest.mark.asyncio
    async def test_detect_markdown(self, parser, sample_markdown):
        """Test auto-detection for markdown files."""
        result = await parser.parse(sample_markdown, "document.md")

        assert result.content is not None
        assert result.metadata.get("detected_parser") == "markdown"

    @pytest.mark.asyncio
    async def test_detect_html(self, parser, sample_html):
        """Test auto-detection for HTML files."""
        result = await parser.parse(sample_html, "document.html")

        assert result.content is not None
        assert result.metadata.get("detected_parser") == "html"

    @pytest.mark.asyncio
    async def test_detect_csv(self, parser, sample_csv):
        """Test auto-detection for CSV files."""
        result = await parser.parse(sample_csv, "data.csv")

        assert result.content is not None
        assert result.metadata.get("detected_parser") == "csv"

    @pytest.mark.asyncio
    async def test_fallback_to_text(self, parser):
        """Test fallback to text parser for unknown types."""
        content = b"Some random content without extension"
        result = await parser.parse(content, "unknown_file")

        assert result.content is not None


class TestParserFactory:
    """Tests for ParserFactory."""

    def test_create_all_parsers(self):
        """Test creating all registered parsers."""
        from app.components.parsers import ParserFactory

        parser_types = ["auto", "text", "markdown", "html", "csv", "pdf", "docx"]

        for parser_type in parser_types:
            parser = ParserFactory.create(parser_type)
            assert parser is not None
            assert parser.name == parser_type

    def test_list_available(self):
        """Test listing available parsers."""
        from app.components.parsers import ParserFactory

        parsers = ParserFactory.list_available()
        assert len(parsers) >= 5
        names = [p["name"] for p in parsers]
        assert "auto" in names
        assert "text" in names

    def test_create_invalid_parser(self):
        """Test creating invalid parser raises error."""
        from app.components.parsers import ParserFactory
        from app.components.base import ComponentNotFoundError

        with pytest.raises(ComponentNotFoundError):
            ParserFactory.create("nonexistent")
