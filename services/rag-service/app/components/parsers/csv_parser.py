"""CSV document parser."""

import csv
import io
from typing import Any, Dict, List

from app.components.parsers.base import BaseParser, ParsedDocument
from app.components.parsers.factory import ParserFactory


class CSVParser(BaseParser):
    """Parser for CSV files."""

    name: str = "csv"
    description: str = "Parser for CSV files with structured data extraction"
    supported_extensions: List[str] = ["csv", "tsv"]

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
                "delimiter": {
                    "type": "string",
                    "default": ",",
                    "description": "Field delimiter (auto-detect if empty)",
                },
                "has_header": {
                    "type": "boolean",
                    "default": True,
                    "description": "First row is header",
                },
                "max_rows": {
                    "type": "integer",
                    "default": 0,
                    "description": "Maximum rows to parse (0 = all)",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["text", "markdown"],
                    "default": "text",
                    "description": "Output format for text content",
                },
            },
        }

    async def parse(
        self,
        content: bytes,
        filename: str,
        encoding: str = "utf-8",
        delimiter: str = "",
        has_header: bool = True,
        max_rows: int = 0,
        output_format: str = "text",
        **kwargs,
    ) -> ParsedDocument:
        """Parse CSV content.

        Args:
            content: Raw CSV content as bytes
            filename: Original filename
            encoding: Text encoding
            delimiter: Field delimiter (auto-detect if empty)
            has_header: Whether first row is header
            max_rows: Maximum rows to parse
            output_format: Output format (text or markdown)

        Returns:
            ParsedDocument with extracted content
        """
        # Decode content
        try:
            text = content.decode(encoding)
        except UnicodeDecodeError:
            text = content.decode("utf-8", errors="replace")

        # Auto-detect delimiter if not specified
        if not delimiter:
            if filename.lower().endswith(".tsv"):
                delimiter = "\t"
            else:
                # Try to sniff the delimiter
                try:
                    sample = text[:8192]
                    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
                    delimiter = dialect.delimiter
                except csv.Error:
                    delimiter = ","

        # Parse CSV
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)

        rows = []
        header = None

        for i, row in enumerate(reader):
            if max_rows > 0 and i >= max_rows:
                break

            if i == 0 and has_header:
                header = row
            else:
                rows.append(row)

        # Build metadata
        metadata = {
            "filename": filename,
            "format": "csv",
            "delimiter": delimiter,
            "row_count": len(rows),
            "column_count": len(header) if header else (len(rows[0]) if rows else 0),
        }

        if header:
            metadata["columns"] = header

        # Convert to text
        if output_format == "markdown":
            output_text = self._to_markdown(header, rows)
        else:
            output_text = self._to_text(header, rows)

        # Store as table data
        tables = [{
            "index": 0,
            "rows": len(rows),
            "cols": len(header) if header else (len(rows[0]) if rows else 0),
            "header": header,
            "content": rows,
        }]

        return ParsedDocument(
            content=output_text,
            metadata=metadata,
            tables=tables,
        )

    def _to_text(self, header: List[str], rows: List[List[str]]) -> str:
        """Convert CSV to plain text format."""
        lines = []

        if header:
            lines.append(" | ".join(header))
            lines.append("-" * 40)

        for row in rows:
            lines.append(" | ".join(row))

        return "\n".join(lines)

    def _to_markdown(self, header: List[str], rows: List[List[str]]) -> str:
        """Convert CSV to markdown table format."""
        lines = []

        if header:
            lines.append("| " + " | ".join(header) + " |")
            lines.append("|" + "|".join(["---"] * len(header)) + "|")

        for row in rows:
            # Pad row to match header length if needed
            if header and len(row) < len(header):
                row = row + [""] * (len(header) - len(row))
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines)


# Register with factory
ParserFactory.register("csv", CSVParser)
