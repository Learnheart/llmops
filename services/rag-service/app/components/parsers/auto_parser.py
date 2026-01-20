"""Auto-detection parser that selects the appropriate parser based on file type."""

import mimetypes
from typing import Any, Dict, List

from app.components.parsers.base import BaseParser, ParsedDocument
from app.components.parsers.factory import ParserFactory


class AutoParser(BaseParser):
    """Parser that auto-detects file type and delegates to the appropriate parser."""

    name: str = "auto"
    description: str = "Automatically detects file type and uses the appropriate parser"
    supported_extensions: List[str] = ["*"]

    # Extension to parser mapping
    EXTENSION_MAP = {
        # Text
        "txt": "text",
        "text": "text",
        # Markdown
        "md": "markdown",
        "markdown": "markdown",
        "mdown": "markdown",
        "mkd": "markdown",
        # PDF
        "pdf": "pdf",
        # Word
        "docx": "docx",
        # HTML
        "html": "html",
        "htm": "html",
        "xhtml": "html",
        # CSV
        "csv": "csv",
        "tsv": "csv",
    }

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "fallback_parser": {
                    "type": "string",
                    "default": "text",
                    "description": "Parser to use if file type cannot be detected",
                },
                "parser_config": {
                    "type": "object",
                    "default": {},
                    "description": "Configuration to pass to the detected parser",
                },
            },
        }

    async def parse(
        self,
        content: bytes,
        filename: str,
        fallback_parser: str = "text",
        parser_config: Dict[str, Any] = None,
        **kwargs,
    ) -> ParsedDocument:
        """Parse content using auto-detected parser.

        Args:
            content: Raw file content as bytes
            filename: Original filename (used for type detection)
            fallback_parser: Parser to use if type cannot be detected
            parser_config: Configuration to pass to the parser

        Returns:
            ParsedDocument with extracted content
        """
        parser_config = parser_config or {}

        # Detect file type from extension
        parser_name = self._detect_parser(filename)

        if not parser_name:
            # Try content-based detection
            parser_name = self._detect_from_content(content)

        if not parser_name:
            parser_name = fallback_parser

        # Get the appropriate parser
        try:
            parser = ParserFactory.create(parser_name)
        except Exception:
            # Fall back to text parser
            parser = ParserFactory.create("text")

        # Parse with the detected parser
        result = await parser.parse(content, filename, **parser_config, **kwargs)

        # Add detection info to metadata
        result.metadata["detected_parser"] = parser_name
        result.metadata["auto_detected"] = True

        return result

    def _detect_parser(self, filename: str) -> str:
        """Detect parser from filename extension."""
        if not filename:
            return ""

        # Get extension
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        return self.EXTENSION_MAP.get(ext, "")

    def _detect_from_content(self, content: bytes) -> str:
        """Detect file type from content magic bytes."""
        if not content:
            return ""

        # Check magic bytes
        if content.startswith(b"%PDF"):
            return "pdf"

        if content.startswith(b"PK\x03\x04"):
            # Could be DOCX, XLSX, etc.
            # DOCX files have specific internal structure
            if b"word/" in content[:2000]:
                return "docx"

        if content.startswith(b"<!DOCTYPE html") or content.startswith(b"<html"):
            return "html"

        # Check for XML/HTML-like content
        if content.startswith(b"<?xml") or content.startswith(b"<"):
            # Try to detect if it's HTML
            lower_content = content[:1000].lower()
            if b"<html" in lower_content or b"<body" in lower_content:
                return "html"

        # Check for markdown indicators
        if content.startswith(b"#") or b"\n#" in content[:500]:
            return "markdown"

        # Default to text for everything else
        return ""


# Register with factory
ParserFactory.register("auto", AutoParser)
