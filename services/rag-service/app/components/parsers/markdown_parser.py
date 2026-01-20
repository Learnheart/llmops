"""Markdown document parser."""

import re
from typing import Any, Dict, List, Optional

from app.components.parsers.base import BaseParser, ParsedDocument
from app.components.parsers.factory import ParserFactory


class MarkdownParser(BaseParser):
    """Parser for Markdown documents."""

    name: str = "markdown"
    description: str = "Parser for Markdown files (.md, .markdown) with structure preservation"
    supported_extensions: List[str] = ["md", "markdown", "mdown", "mkd"]

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "encoding": {
                    "type": "string",
                    "default": "utf-8",
                    "description": "Text encoding",
                },
                "preserve_structure": {
                    "type": "boolean",
                    "default": True,
                    "description": "Preserve markdown structure in output",
                },
                "extract_code_blocks": {
                    "type": "boolean",
                    "default": True,
                    "description": "Extract code blocks separately",
                },
                "remove_html": {
                    "type": "boolean",
                    "default": False,
                    "description": "Remove inline HTML tags",
                },
            },
        }

    async def parse(
        self,
        content: bytes,
        filename: str,
        encoding: str = "utf-8",
        preserve_structure: bool = True,
        extract_code_blocks: bool = True,
        remove_html: bool = False,
        **kwargs,
    ) -> ParsedDocument:
        """Parse Markdown content.

        Args:
            content: Raw file content as bytes
            filename: Original filename
            encoding: Text encoding
            preserve_structure: Keep markdown formatting
            extract_code_blocks: Extract code blocks with metadata
            remove_html: Strip HTML tags

        Returns:
            ParsedDocument with parsed content
        """
        try:
            text = content.decode(encoding)
        except UnicodeDecodeError:
            text = content.decode("utf-8", errors="replace")

        # Extract metadata
        metadata = {
            "filename": filename,
            "format": "markdown",
        }

        # Extract title from first heading
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if title_match:
            metadata["title"] = title_match.group(1).strip()

        # Extract headers structure
        headers = self._extract_headers(text)
        if headers:
            metadata["headers"] = headers

        # Extract code blocks if requested
        code_blocks = []
        if extract_code_blocks:
            code_blocks = self._extract_code_blocks(text)
            if code_blocks:
                metadata["code_blocks"] = len(code_blocks)

        # Process text
        processed_text = text
        if remove_html:
            processed_text = re.sub(r"<[^>]+>", "", processed_text)

        if not preserve_structure:
            # Convert to plain text
            processed_text = self._to_plain_text(processed_text)

        return ParsedDocument(
            content=processed_text.strip(),
            metadata=metadata,
        )

    def _extract_headers(self, text: str) -> List[Dict[str, Any]]:
        """Extract markdown headers with their levels."""
        headers = []
        pattern = r"^(#{1,6})\s+(.+)$"

        for match in re.finditer(pattern, text, re.MULTILINE):
            level = len(match.group(1))
            title = match.group(2).strip()
            headers.append({
                "level": level,
                "title": title,
                "position": match.start(),
            })

        return headers

    def _extract_code_blocks(self, text: str) -> List[Dict[str, Any]]:
        """Extract fenced code blocks."""
        code_blocks = []
        pattern = r"```(\w*)\n(.*?)```"

        for match in re.finditer(pattern, text, re.DOTALL):
            language = match.group(1) or "text"
            code = match.group(2).strip()
            code_blocks.append({
                "language": language,
                "code": code,
                "position": match.start(),
            })

        return code_blocks

    def _to_plain_text(self, text: str) -> str:
        """Convert markdown to plain text."""
        # Remove code blocks (preserve content)
        text = re.sub(r"```\w*\n", "", text)
        text = re.sub(r"```", "", text)

        # Remove headers markers
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

        # Remove emphasis markers
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\*(.+?)\*", r"\1", text)
        text = re.sub(r"__(.+?)__", r"\1", text)
        text = re.sub(r"_(.+?)_", r"\1", text)

        # Remove links but keep text
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

        # Remove images
        text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)

        # Remove inline code markers
        text = re.sub(r"`([^`]+)`", r"\1", text)

        # Remove blockquote markers
        text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)

        # Remove horizontal rules
        text = re.sub(r"^[-*_]{3,}$", "", text, flags=re.MULTILINE)

        return text


# Register with factory
ParserFactory.register("markdown", MarkdownParser)
