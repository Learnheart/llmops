"""PDF document parser using PyMuPDF."""

from typing import Any, Dict, List, Optional

from app.components.parsers.base import BaseParser, ParsedDocument
from app.components.parsers.factory import ParserFactory


class PDFParser(BaseParser):
    """Parser for PDF documents using PyMuPDF (fitz)."""

    name: str = "pdf"
    description: str = "Parser for PDF documents with text extraction and optional table detection"
    supported_extensions: List[str] = ["pdf"]

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "extract_tables": {
                    "type": "boolean",
                    "default": True,
                    "description": "Attempt to extract tables",
                },
                "extract_images": {
                    "type": "boolean",
                    "default": False,
                    "description": "Extract image metadata",
                },
                "page_separator": {
                    "type": "string",
                    "default": "\n\n---\n\n",
                    "description": "Separator between pages",
                },
                "preserve_layout": {
                    "type": "boolean",
                    "default": False,
                    "description": "Try to preserve text layout",
                },
            },
        }

    async def parse(
        self,
        content: bytes,
        filename: str,
        extract_tables: bool = True,
        extract_images: bool = False,
        page_separator: str = "\n\n---\n\n",
        preserve_layout: bool = False,
        **kwargs,
    ) -> ParsedDocument:
        """Parse PDF content.

        Args:
            content: Raw PDF content as bytes
            filename: Original filename
            extract_tables: Whether to extract tables
            extract_images: Whether to extract image metadata
            page_separator: String to separate pages
            preserve_layout: Try to preserve original layout

        Returns:
            ParsedDocument with extracted content
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError("PyMuPDF (fitz) is required for PDF parsing. "
                              "Install with: pip install pymupdf")

        # Open PDF from bytes
        doc = fitz.open(stream=content, filetype="pdf")

        # Extract metadata
        metadata = {
            "filename": filename,
            "format": "pdf",
            "page_count": doc.page_count,
        }

        # Get document metadata
        pdf_metadata = doc.metadata
        if pdf_metadata:
            if pdf_metadata.get("title"):
                metadata["title"] = pdf_metadata["title"]
            if pdf_metadata.get("author"):
                metadata["author"] = pdf_metadata["author"]
            if pdf_metadata.get("subject"):
                metadata["subject"] = pdf_metadata["subject"]
            if pdf_metadata.get("creationDate"):
                metadata["creation_date"] = pdf_metadata["creationDate"]

        # Extract text from each page
        pages = []
        all_text = []
        tables = []
        images = []

        for page_num, page in enumerate(doc):
            # Extract text
            if preserve_layout:
                text = page.get_text("text", sort=True)
            else:
                text = page.get_text()

            text = text.strip()
            all_text.append(text)

            page_data = {
                "page_number": page_num + 1,
                "text": text,
                "width": page.rect.width,
                "height": page.rect.height,
            }

            # Extract tables if requested
            if extract_tables:
                page_tables = self._extract_tables(page)
                if page_tables:
                    page_data["tables"] = page_tables
                    tables.extend(page_tables)

            # Extract images if requested
            if extract_images:
                page_images = self._extract_images(page, page_num + 1)
                if page_images:
                    page_data["images"] = page_images
                    images.extend(page_images)

            pages.append(page_data)

        doc.close()

        # Combine all text
        full_text = page_separator.join(all_text)

        return ParsedDocument(
            content=full_text,
            metadata=metadata,
            pages=pages,
            tables=tables if tables else None,
            images=images if images else None,
        )

    def _extract_tables(self, page) -> List[Dict[str, Any]]:
        """Extract tables from a PDF page."""
        tables = []

        try:
            # Use PyMuPDF's table detection
            tab_finder = page.find_tables()
            for i, table in enumerate(tab_finder):
                table_data = {
                    "index": i,
                    "bbox": list(table.bbox),
                    "rows": len(table.cells) if hasattr(table, "cells") else 0,
                }

                # Extract table content
                try:
                    extracted = table.extract()
                    if extracted:
                        table_data["content"] = extracted
                        table_data["rows"] = len(extracted)
                        table_data["cols"] = len(extracted[0]) if extracted else 0
                except Exception:
                    pass

                tables.append(table_data)
        except Exception:
            # Table extraction not available or failed
            pass

        return tables

    def _extract_images(self, page, page_num: int) -> List[Dict[str, Any]]:
        """Extract image metadata from a PDF page."""
        images = []

        try:
            image_list = page.get_images()
            for img_index, img in enumerate(image_list):
                xref = img[0]
                images.append({
                    "index": img_index,
                    "page": page_num,
                    "xref": xref,
                    "width": img[2],
                    "height": img[3],
                })
        except Exception:
            pass

        return images


# Register with factory
ParserFactory.register("pdf", PDFParser)
