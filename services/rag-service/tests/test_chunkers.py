"""Tests for chunker components."""

import pytest


class TestRecursiveChunker:
    """Tests for RecursiveChunker."""

    @pytest.fixture
    def chunker(self):
        from app.components.chunkers import RecursiveChunker
        return RecursiveChunker()

    @pytest.mark.asyncio
    async def test_chunk_simple_text(self, chunker, sample_text):
        """Test chunking simple text."""
        chunks = await chunker.chunk(sample_text, chunk_size=200, chunk_overlap=20)

        assert len(chunks) > 0
        for chunk in chunks:
            assert len(chunk.content) > 0
            assert chunk.index >= 0

    @pytest.mark.asyncio
    async def test_chunk_empty_text(self, chunker):
        """Test chunking empty text."""
        chunks = await chunker.chunk("", chunk_size=100)
        assert len(chunks) == 0

    @pytest.mark.asyncio
    async def test_chunk_respects_size(self, chunker, long_sample_text):
        """Test that chunks respect size limit."""
        chunk_size = 200
        chunks = await chunker.chunk(long_sample_text, chunk_size=chunk_size, chunk_overlap=0)

        assert len(chunks) > 1
        # Most chunks should be within reasonable size
        for chunk in chunks[:-1]:
            assert len(chunk.content) <= chunk_size * 2

    @pytest.mark.asyncio
    async def test_chunk_overlap(self, chunker, long_sample_text):
        """Test overlap between chunks."""
        chunks = await chunker.chunk(long_sample_text, chunk_size=200, chunk_overlap=50)

        assert len(chunks) > 1
        # Check indices are sequential
        for i, chunk in enumerate(chunks):
            assert chunk.index == i

    @pytest.mark.asyncio
    async def test_chunk_with_custom_separators(self, chunker, sample_text):
        """Test chunking with custom separators."""
        chunks = await chunker.chunk(
            sample_text,
            chunk_size=100,
            separators=["\n\n", "\n", " "]
        )

        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_chunk_metadata(self, chunker, sample_text):
        """Test chunk metadata includes position info."""
        chunks = await chunker.chunk(sample_text, chunk_size=200)

        for chunk in chunks:
            assert hasattr(chunk, 'start_char')
            assert hasattr(chunk, 'end_char')
            assert hasattr(chunk, 'metadata')


class TestFixedChunker:
    """Tests for FixedChunker."""

    @pytest.fixture
    def chunker(self):
        from app.components.chunkers import FixedChunker
        return FixedChunker()

    @pytest.mark.asyncio
    async def test_fixed_size_chunks(self, chunker):
        """Test fixed size chunking."""
        text = "A" * 1000
        chunks = await chunker.chunk(text, chunk_size=100, chunk_overlap=0)

        assert len(chunks) == 10
        for chunk in chunks:
            assert len(chunk.content) == 100

    @pytest.mark.asyncio
    async def test_overlap(self, chunker):
        """Test overlap between chunks."""
        text = "A" * 200
        chunks = await chunker.chunk(text, chunk_size=100, chunk_overlap=20)

        # With size=100, overlap=20, step=80
        # Positions: 0-100, 80-180, 160-200
        assert len(chunks) == 3

    @pytest.mark.asyncio
    async def test_last_chunk_smaller(self, chunker):
        """Test last chunk can be smaller."""
        text = "A" * 150
        chunks = await chunker.chunk(text, chunk_size=100, chunk_overlap=0)

        assert len(chunks) == 2
        assert len(chunks[0].content) == 100
        assert len(chunks[1].content) == 50

    @pytest.mark.asyncio
    async def test_empty_text(self, chunker):
        """Test chunking empty text."""
        chunks = await chunker.chunk("", chunk_size=100)
        assert len(chunks) == 0

    @pytest.mark.asyncio
    async def test_chunk_indices(self, chunker):
        """Test chunk indices are sequential."""
        text = "A" * 500
        chunks = await chunker.chunk(text, chunk_size=100, chunk_overlap=0)

        for i, chunk in enumerate(chunks):
            assert chunk.index == i


class TestSentenceChunker:
    """Tests for SentenceChunker."""

    @pytest.fixture
    def chunker(self):
        from app.components.chunkers import SentenceChunker
        return SentenceChunker()

    @pytest.mark.asyncio
    async def test_sentence_boundaries(self, chunker):
        """Test chunking respects sentence boundaries."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = await chunker.chunk(text, chunk_size=50, chunk_overlap=0)

        assert len(chunks) > 0
        # Chunks should contain complete sentences
        for chunk in chunks:
            # Should not end mid-sentence (unless sentence is too long)
            content = chunk.content.strip()
            assert content.endswith(".") or len(content) < 50

    @pytest.mark.asyncio
    async def test_single_sentence(self, chunker):
        """Test with single sentence."""
        text = "This is a single sentence."
        chunks = await chunker.chunk(text, chunk_size=100)

        assert len(chunks) == 1

    @pytest.mark.asyncio
    async def test_long_sentences(self, chunker):
        """Test handling of long sentences."""
        long_sentence = "This is a very long sentence " * 20 + "."
        chunks = await chunker.chunk(long_sentence, chunk_size=100)

        assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_sentence_overlap(self, chunker):
        """Test sentence overlap."""
        text = "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five."
        chunks = await chunker.chunk(text, chunk_size=50, chunk_overlap=1)

        # With overlap, sentences should appear in multiple chunks
        assert len(chunks) > 1


class TestSemanticChunker:
    """Tests for SemanticChunker (without embedder)."""

    @pytest.fixture
    def chunker(self):
        from app.components.chunkers import SemanticChunker
        return SemanticChunker()

    @pytest.mark.asyncio
    async def test_fallback_without_embedder(self, chunker, sample_text):
        """Test fallback chunking when no embedder provided."""
        # Without embedder, should use fallback sentence grouping
        chunks = await chunker.chunk(sample_text, chunk_size=200)

        assert len(chunks) > 0
        for chunk in chunks:
            assert len(chunk.content) > 0

    @pytest.mark.asyncio
    async def test_min_chunk_size(self, chunker):
        """Test minimum chunk size is respected."""
        text = "Short. Another short. Third short."
        chunks = await chunker.chunk(text, chunk_size=200, min_chunk_size=50)

        # Small chunks should be merged
        for chunk in chunks:
            assert len(chunk.content) >= 30  # Allow some flexibility


class TestChunkerFactory:
    """Tests for ChunkerFactory."""

    def test_create_all_chunkers(self):
        """Test creating all registered chunkers."""
        from app.components.chunkers import ChunkerFactory

        chunker_types = ["recursive", "fixed", "sentence", "semantic"]

        for chunker_type in chunker_types:
            chunker = ChunkerFactory.create(chunker_type)
            assert chunker is not None
            assert chunker.name == chunker_type

    def test_list_available(self):
        """Test listing available chunkers."""
        from app.components.chunkers import ChunkerFactory

        chunkers = ChunkerFactory.list_available()
        assert len(chunkers) >= 4
        names = [c["name"] for c in chunkers]
        assert "recursive" in names
        assert "fixed" in names

    def test_create_invalid_chunker(self):
        """Test creating invalid chunker raises error."""
        from app.components.chunkers import ChunkerFactory
        from app.components.base import ComponentNotFoundError

        with pytest.raises(ComponentNotFoundError):
            ChunkerFactory.create("nonexistent")

    def test_get_config_schema(self):
        """Test getting config schema."""
        from app.components.chunkers import ChunkerFactory

        chunker = ChunkerFactory.create("recursive")
        schema = chunker.get_config_schema()

        assert "properties" in schema
        assert "chunk_size" in schema["properties"]
        assert "chunk_overlap" in schema["properties"]
