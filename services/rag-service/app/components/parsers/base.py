"""Base parser class for document parsing."""

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.components.base.component import BaseComponent


@dataclass
class ParsedDocument:
    """Result of document parsing."""

    content: str
    """Extracted text content from the document."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Document metadata (title, author, etc.)."""

    pages: Optional[List[Dict[str, Any]]] = None
    """Page-by-page content if applicable."""

    tables: Optional[List[Dict[str, Any]]] = None
    """Extracted tables if any."""

    images: Optional[List[Dict[str, Any]]] = None
    """Extracted image references if any."""


class BaseParser(BaseComponent):
    """Abstract base class for document parsers.

    Parsers extract text content from various document formats
    (PDF, DOCX, HTML, Markdown, etc.).
    """

    category: str = "parsers"
    supported_extensions: List[str] = []

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Return configuration schema for parser."""
        return {
            "type": "object",
            "properties": {
                "extract_tables": {
                    "type": "boolean",
                    "default": True,
                    "description": "Extract tables as structured text",
                },
                "extract_images": {
                    "type": "boolean",
                    "default": False,
                    "description": "Extract image references",
                },
                "encoding": {
                    "type": "string",
                    "default": "utf-8",
                    "description": "Text encoding for parsing",
                },
            },
        }

    @abstractmethod
    async def parse(
        self,
        content: bytes,
        filename: str,
        **kwargs,
    ) -> ParsedDocument:
        """Parse document content and extract text.

        Args:
            content: Raw file content as bytes
            filename: Original filename (used for format detection)
            **kwargs: Additional parser-specific options

        Returns:
            ParsedDocument with extracted content and metadata
        """
        pass

    async def process(
        self,
        input_data: Any,
        config: Optional[Dict[str, Any]] = None,
    ) -> ParsedDocument:
        """Process method implementing BaseComponent interface.

        Args:
            input_data: Tuple of (content: bytes, filename: str)
            config: Parser configuration options

        Returns:
            ParsedDocument with extracted content
        """
        if isinstance(input_data, tuple):
            content, filename = input_data
        else:
            raise ValueError("Input must be tuple of (content: bytes, filename: str)")

        return await self.parse(content, filename, **(config or {}))

    def supports_extension(self, extension: str) -> bool:
        """Check if this parser supports the given file extension.

        Args:
            extension: File extension (with or without dot)

        Returns:
            True if supported, False otherwise
        """
        ext = extension.lower().lstrip(".")
        return ext in self.supported_extensions
