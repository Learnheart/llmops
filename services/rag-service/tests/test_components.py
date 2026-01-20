"""Tests for component registry and factories."""

import pytest
from app.components.base.registry import ComponentRegistry
from app.components.parsers.factory import ParserFactory
from app.components.chunkers.factory import ChunkerFactory


class TestComponentRegistry:
    """Tests for ComponentRegistry."""

    def test_list_categories(self):
        """Test listing all categories."""
        # Import to register components
        from app.components.parsers import AutoParser
        from app.components.chunkers import RecursiveChunker

        categories = ComponentRegistry.list_categories()
        assert "parsers" in categories
        assert "chunkers" in categories

    def test_get_all_components(self):
        """Test getting all components."""
        from app.components.parsers import AutoParser

        components = ComponentRegistry.get_all_components()
        assert isinstance(components, dict)


class TestParserFactory:
    """Tests for ParserFactory."""

    def test_create_auto_parser(self):
        """Test creating auto parser."""
        from app.components.parsers import AutoParser

        parser = ParserFactory.create("auto")
        assert parser.name == "auto"

    def test_create_text_parser(self):
        """Test creating text parser."""
        from app.components.parsers import TextParser

        parser = ParserFactory.create("text")
        assert parser.name == "text"

    def test_list_available_parsers(self):
        """Test listing available parsers."""
        from app.components.parsers import AutoParser, TextParser

        parsers = ParserFactory.list_available()
        assert len(parsers) > 0


class TestChunkerFactory:
    """Tests for ChunkerFactory."""

    def test_create_recursive_chunker(self):
        """Test creating recursive chunker."""
        from app.components.chunkers import RecursiveChunker

        chunker = ChunkerFactory.create("recursive")
        assert chunker.name == "recursive"

    def test_create_fixed_chunker(self):
        """Test creating fixed chunker."""
        from app.components.chunkers import FixedChunker

        chunker = ChunkerFactory.create("fixed")
        assert chunker.name == "fixed"
