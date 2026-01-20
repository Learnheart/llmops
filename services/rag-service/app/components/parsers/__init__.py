"""Document parser components."""

from app.components.parsers.base import BaseParser, ParsedDocument
from app.components.parsers.factory import ParserFactory
from app.components.parsers.auto_parser import AutoParser
from app.components.parsers.pdf_parser import PDFParser
from app.components.parsers.markdown_parser import MarkdownParser
from app.components.parsers.text_parser import TextParser
from app.components.parsers.docx_parser import DocxParser
from app.components.parsers.html_parser import HTMLParser
from app.components.parsers.csv_parser import CSVParser

__all__ = [
    "BaseParser",
    "ParsedDocument",
    "ParserFactory",
    "AutoParser",
    "PDFParser",
    "MarkdownParser",
    "TextParser",
    "DocxParser",
    "HTMLParser",
    "CSVParser",
]
