"""Semantic chunker using embeddings to detect topic boundaries."""

from typing import Any, Dict, List, Optional
import numpy as np

from app.components.chunkers.base import BaseChunker, Chunk
from app.components.chunkers.factory import ChunkerFactory


class SemanticChunker(BaseChunker):
    """Chunker that uses embeddings to detect semantic boundaries.

    Splits text at points where the topic changes significantly,
    as measured by cosine similarity between adjacent text segments.
    """

    name: str = "semantic"
    description: str = "Uses embeddings to detect topic boundaries for more meaningful chunks"

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "chunk_size": {
                    "type": "integer",
                    "default": 512,
                    "description": "Maximum size of each chunk",
                    "minimum": 100,
                    "maximum": 8192,
                },
                "min_chunk_size": {
                    "type": "integer",
                    "default": 100,
                    "description": "Minimum size of each chunk",
                    "minimum": 50,
                },
                "similarity_threshold": {
                    "type": "number",
                    "default": 0.5,
                    "description": "Threshold for detecting topic change (0-1)",
                    "minimum": 0.0,
                    "maximum": 1.0,
                },
                "sentence_window": {
                    "type": "integer",
                    "default": 3,
                    "description": "Number of sentences to use for similarity calculation",
                    "minimum": 1,
                },
            },
        }

    def __init__(self):
        """Initialize semantic chunker."""
        super().__init__()
        self._embedder = None

    async def chunk(
        self,
        text: str,
        chunk_size: int = 512,
        min_chunk_size: int = 100,
        similarity_threshold: float = 0.5,
        sentence_window: int = 3,
        embedder=None,
        **kwargs,
    ) -> List[Chunk]:
        """Split text at semantic boundaries.

        Args:
            text: Text to split
            chunk_size: Maximum chunk size
            min_chunk_size: Minimum chunk size
            similarity_threshold: Threshold for topic change detection
            sentence_window: Sentences to use for similarity
            embedder: Embedder instance to use (optional)

        Returns:
            List of Chunk objects
        """
        if not text:
            return []

        # Split into sentences first
        sentences = self._split_sentences(text)

        if len(sentences) <= 1:
            return [self._create_chunk(content=text, index=0, start_char=0, end_char=len(text))]

        # If no embedder provided, fall back to simple chunking
        if embedder is None:
            return await self._fallback_chunk(text, sentences, chunk_size, min_chunk_size)

        # Calculate embeddings for sentence windows
        try:
            embeddings = await self._get_window_embeddings(sentences, sentence_window, embedder)
        except Exception:
            # Fall back if embedding fails
            return await self._fallback_chunk(text, sentences, chunk_size, min_chunk_size)

        # Find break points based on similarity
        break_points = self._find_break_points(embeddings, similarity_threshold)

        # Create chunks from break points
        chunks = self._create_chunks_from_breaks(
            text=text,
            sentences=sentences,
            break_points=break_points,
            chunk_size=chunk_size,
            min_chunk_size=min_chunk_size,
        )

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        import re

        # Split by sentence endings
        pattern = r'(?<=[.!?])\s+'
        sentences = re.split(pattern, text)

        return [s.strip() for s in sentences if s.strip()]

    async def _get_window_embeddings(
        self,
        sentences: List[str],
        window_size: int,
        embedder,
    ) -> List[np.ndarray]:
        """Get embeddings for sentence windows."""
        windows = []
        for i in range(len(sentences)):
            start = max(0, i - window_size // 2)
            end = min(len(sentences), i + window_size // 2 + 1)
            window_text = " ".join(sentences[start:end])
            windows.append(window_text)

        # Get embeddings
        embeddings = await embedder.embed(windows)
        return embeddings

    def _find_break_points(
        self,
        embeddings: List[np.ndarray],
        threshold: float,
    ) -> List[int]:
        """Find indices where topic changes significantly."""
        if len(embeddings) < 2:
            return []

        break_points = []

        for i in range(1, len(embeddings)):
            similarity = self._cosine_similarity(embeddings[i-1], embeddings[i])

            if similarity < threshold:
                break_points.append(i)

        return break_points

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        a = np.array(a)
        b = np.array(b)

        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def _create_chunks_from_breaks(
        self,
        text: str,
        sentences: List[str],
        break_points: List[int],
        chunk_size: int,
        min_chunk_size: int,
    ) -> List[Chunk]:
        """Create chunks from break points."""
        chunks = []

        # Add start and end
        all_breaks = [0] + break_points + [len(sentences)]

        current_pos = 0
        for i in range(len(all_breaks) - 1):
            start_idx = all_breaks[i]
            end_idx = all_breaks[i + 1]

            chunk_sentences = sentences[start_idx:end_idx]
            chunk_text = " ".join(chunk_sentences)

            # Enforce size constraints
            if len(chunk_text) > chunk_size:
                # Split large chunks
                sub_chunks = self._split_large_chunk(chunk_text, chunk_size)
                for sub_text in sub_chunks:
                    if len(sub_text) >= min_chunk_size:
                        start_char = text.find(sub_text[:50], current_pos) if len(sub_text) >= 50 else current_pos
                        chunks.append(
                            self._create_chunk(
                                content=sub_text,
                                index=len(chunks),
                                start_char=start_char,
                                end_char=start_char + len(sub_text),
                            )
                        )
                        current_pos = start_char + len(sub_text)
            elif len(chunk_text) >= min_chunk_size:
                start_char = text.find(chunk_sentences[0], current_pos) if chunk_sentences else current_pos
                chunks.append(
                    self._create_chunk(
                        content=chunk_text,
                        index=len(chunks),
                        start_char=start_char,
                        end_char=start_char + len(chunk_text),
                    )
                )
                current_pos = start_char + len(chunk_text)

        return chunks

    def _split_large_chunk(self, text: str, max_size: int) -> List[str]:
        """Split a chunk that's too large."""
        chunks = []
        words = text.split()
        current = []
        current_len = 0

        for word in words:
            if current_len + len(word) + 1 > max_size and current:
                chunks.append(" ".join(current))
                current = [word]
                current_len = len(word)
            else:
                current.append(word)
                current_len += len(word) + 1

        if current:
            chunks.append(" ".join(current))

        return chunks

    async def _fallback_chunk(
        self,
        text: str,
        sentences: List[str],
        chunk_size: int,
        min_chunk_size: int,
    ) -> List[Chunk]:
        """Fallback to simple sentence grouping without embeddings."""
        chunks = []
        current_sentences = []
        current_length = 0

        for sentence in sentences:
            if current_length + len(sentence) > chunk_size and current_sentences:
                chunk_text = " ".join(current_sentences)
                if len(chunk_text) >= min_chunk_size:
                    chunks.append(
                        self._create_chunk(
                            content=chunk_text,
                            index=len(chunks),
                        )
                    )
                current_sentences = [sentence]
                current_length = len(sentence)
            else:
                current_sentences.append(sentence)
                current_length += len(sentence) + 1

        if current_sentences:
            chunk_text = " ".join(current_sentences)
            if len(chunk_text) >= min_chunk_size:
                chunks.append(
                    self._create_chunk(
                        content=chunk_text,
                        index=len(chunks),
                    )
                )

        return chunks


# Register with factory
ChunkerFactory.register("semantic", SemanticChunker)
