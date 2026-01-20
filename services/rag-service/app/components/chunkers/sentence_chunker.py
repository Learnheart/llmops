"""Sentence-based text chunker."""

import re
from typing import Any, Dict, List

from app.components.chunkers.base import BaseChunker, Chunk
from app.components.chunkers.factory import ChunkerFactory


class SentenceChunker(BaseChunker):
    """Chunker that splits text by sentences and groups them into chunks.

    Ensures that chunks always contain complete sentences, which can
    improve retrieval quality for certain types of content.
    """

    name: str = "sentence"
    description: str = "Splits text by sentences and groups them to meet chunk size"

    # Sentence ending patterns
    SENTENCE_ENDINGS = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "chunk_size": {
                    "type": "integer",
                    "default": 512,
                    "description": "Target size of each chunk in characters",
                    "minimum": 50,
                    "maximum": 8192,
                },
                "chunk_overlap": {
                    "type": "integer",
                    "default": 1,
                    "description": "Number of sentences to overlap between chunks",
                    "minimum": 0,
                },
                "min_sentences": {
                    "type": "integer",
                    "default": 1,
                    "description": "Minimum sentences per chunk",
                    "minimum": 1,
                },
            },
        }

    async def chunk(
        self,
        text: str,
        chunk_size: int = 512,
        chunk_overlap: int = 1,
        min_sentences: int = 1,
        **kwargs,
    ) -> List[Chunk]:
        """Split text by sentences and group into chunks.

        Args:
            text: Text to split
            chunk_size: Target chunk size in characters
            chunk_overlap: Number of sentences to overlap
            min_sentences: Minimum sentences per chunk

        Returns:
            List of Chunk objects
        """
        if not text:
            return []

        # Split into sentences
        sentences = self._split_sentences(text)

        if not sentences:
            return [self._create_chunk(content=text, index=0)]

        # Group sentences into chunks
        chunks = []
        current_sentences = []
        current_length = 0
        index = 0

        for i, sentence in enumerate(sentences):
            sentence_length = len(sentence)

            # Check if adding this sentence would exceed chunk_size
            if current_length + sentence_length > chunk_size and len(current_sentences) >= min_sentences:
                # Finalize current chunk
                chunk_text = " ".join(current_sentences)
                start_char = text.find(current_sentences[0])

                chunks.append(
                    self._create_chunk(
                        content=chunk_text,
                        index=index,
                        start_char=start_char,
                        end_char=start_char + len(chunk_text),
                    )
                )
                index += 1

                # Start new chunk with overlap
                if chunk_overlap > 0 and len(current_sentences) > chunk_overlap:
                    current_sentences = current_sentences[-chunk_overlap:]
                    current_length = sum(len(s) for s in current_sentences)
                else:
                    current_sentences = []
                    current_length = 0

            current_sentences.append(sentence)
            current_length += sentence_length

        # Add final chunk
        if current_sentences:
            chunk_text = " ".join(current_sentences)
            start_char = text.find(current_sentences[0])

            chunks.append(
                self._create_chunk(
                    content=chunk_text,
                    index=index,
                    start_char=start_char,
                    end_char=start_char + len(chunk_text),
                )
            )

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # First, split by common sentence boundaries
        sentences = self.SENTENCE_ENDINGS.split(text)

        # Clean up sentences
        result = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                result.append(sentence)

        # If no sentences found, try simpler splitting
        if len(result) <= 1:
            # Split by period, question mark, exclamation
            simple_split = re.split(r'(?<=[.!?])\s+', text)
            result = [s.strip() for s in simple_split if s.strip()]

        return result


# Register with factory
ChunkerFactory.register("sentence", SentenceChunker)
