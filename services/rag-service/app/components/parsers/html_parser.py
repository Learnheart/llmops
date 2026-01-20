"""HTML document parser using BeautifulSoup."""

import re
from typing import Any, Dict, List

from app.components.parsers.base import BaseParser, ParsedDocument
from app.components.parsers.factory import ParserFactory


class HTMLParser(BaseParser):
    """Parser for HTML documents."""

    name: str = "html"
    description: str = "Parser for HTML documents with text extraction and structure preservation"
    supported_extensions: List[str] = ["html", "htm", "xhtml"]

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
                "extract_links": {
                    "type": "boolean",
                    "default": False,
                    "description": "Extract links as metadata",
                },
                "extract_tables": {
                    "type": "boolean",
                    "default": True,
                    "description": "Extract tables",
                },
                "remove_scripts": {
                    "type": "boolean",
                    "default": True,
                    "description": "Remove script and style tags",
                },
                "preserve_newlines": {
                    "type": "boolean",
                    "default": True,
                    "description": "Preserve paragraph breaks",
                },
            },
        }

    async def parse(
        self,
        content: bytes,
        filename: str,
        encoding: str = "utf-8",
        extract_links: bool = False,
        extract_tables: bool = True,
        remove_scripts: bool = True,
        preserve_newlines: bool = True,
        **kwargs,
    ) -> ParsedDocument:
        """Parse HTML content.

        Args:
            content: Raw HTML content as bytes
            filename: Original filename
            encoding: Text encoding
            extract_links: Whether to extract links
            extract_tables: Whether to extract tables
            remove_scripts: Whether to remove script/style tags
            preserve_newlines: Whether to preserve paragraph breaks

        Returns:
            ParsedDocument with extracted content
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError("beautifulsoup4 is required for HTML parsing. "
                              "Install with: pip install beautifulsoup4")

        # Decode content
        try:
            html_text = content.decode(encoding)
        except UnicodeDecodeError:
            html_text = content.decode("utf-8", errors="replace")

        # Parse HTML
        soup = BeautifulSoup(html_text, "lxml")

        # Extract metadata
        metadata = {
            "filename": filename,
            "format": "html",
        }

        # Get title
        title_tag = soup.find("title")
        if title_tag:
            metadata["title"] = title_tag.get_text().strip()

        # Get meta tags
        meta_description = soup.find("meta", attrs={"name": "description"})
        if meta_description:
            metadata["description"] = meta_description.get("content", "")

        meta_keywords = soup.find("meta", attrs={"name": "keywords"})
        if meta_keywords:
            metadata["keywords"] = meta_keywords.get("content", "")

        # Remove unwanted tags
        if remove_scripts:
            for tag in soup.find_all(["script", "style", "noscript"]):
                tag.decompose()

        # Extract headings
        headings = []
        for i in range(1, 7):
            for heading in soup.find_all(f"h{i}"):
                text = heading.get_text().strip()
                if text:
                    headings.append({
                        "level": i,
                        "text": text,
                    })

        if headings:
            metadata["headings"] = headings

        # Extract links if requested
        if extract_links:
            links = []
            for link in soup.find_all("a", href=True):
                text = link.get_text().strip()
                href = link.get("href")
                if href and not href.startswith("#"):
                    links.append({
                        "text": text,
                        "href": href,
                    })
            if links:
                metadata["links"] = links

        # Extract tables if requested
        tables = []
        if extract_tables:
            for i, table in enumerate(soup.find_all("table")):
                table_data = self._extract_table(table, i)
                if table_data["content"]:
                    tables.append(table_data)

        # Get main text content
        if preserve_newlines:
            # Add newlines around block elements
            for tag in soup.find_all(["p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li"]):
                tag.insert_before("\n")
                tag.insert_after("\n")

        text = soup.get_text()

        # Clean up whitespace
        if preserve_newlines:
            # Collapse multiple newlines to two
            text = re.sub(r"\n\s*\n", "\n\n", text)
        else:
            text = re.sub(r"\s+", " ", text)

        text = text.strip()

        return ParsedDocument(
            content=text,
            metadata=metadata,
            tables=tables if tables else None,
        )

    def _extract_table(self, table, index: int) -> Dict[str, Any]:
        """Extract table data from HTML table."""
        rows = []

        # Get header row
        thead = table.find("thead")
        if thead:
            for tr in thead.find_all("tr"):
                cells = []
                for th in tr.find_all(["th", "td"]):
                    cells.append(th.get_text().strip())
                if cells:
                    rows.append(cells)

        # Get body rows
        tbody = table.find("tbody") or table
        for tr in tbody.find_all("tr"):
            cells = []
            for td in tr.find_all(["td", "th"]):
                cells.append(td.get_text().strip())
            if cells:
                rows.append(cells)

        return {
            "index": index,
            "rows": len(rows),
            "cols": len(rows[0]) if rows else 0,
            "content": rows,
        }


# Register with factory
ParserFactory.register("html", HTMLParser)
