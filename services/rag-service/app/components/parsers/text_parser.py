"""Plain text parser."""

from typing import Any, Dict, List

from app.components.parsers.base import BaseParser, ParsedDocument
from app.components.parsers.factory import ParserFactory


class TextParser(BaseParser):
    """Parser for plain text files."""

    name: str = "text"
    description: str = "Parser for plain text files (.txt)"
    supported_extensions: List[str] = ["txt", "text"]

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
                "strip_whitespace": {
                    "type": "boolean",
                    "default": True,
                    "description": "Strip leading/trailing whitespace",
                },
            },
        }

    async def parse(
        self,
        content: bytes,
        filename: str,
        encoding: str = "utf-8",
        strip_whitespace: bool = True,
        **kwargs,
    ) -> ParsedDocument:
        """Parse plain text content.

        Args:
            content: Raw file content as bytes
            filename: Original filename
            encoding: Text encoding
            strip_whitespace: Whether to strip whitespace

        Returns:
            ParsedDocument with text content
        """
        try:
            text = content.decode(encoding)
        except UnicodeDecodeError:
            # Try common fallback encodings
            for enc in ["latin-1", "cp1252", "iso-8859-1"]:
                try:
                    text = content.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                text = content.decode("utf-8", errors="replace")

        if strip_whitespace:
            text = text.strip()

        return ParsedDocument(
            content=text,
            metadata={
                "filename": filename,
                "encoding": encoding,
                "character_count": len(text),
                "line_count": text.count("\n") + 1,
            },
        )


# Register with factory
ParserFactory.register("text", TextParser)
