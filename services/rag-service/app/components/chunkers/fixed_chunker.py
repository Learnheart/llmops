"""Fixed-size text chunker."""

from typing import Any, Dict, List

from app.components.chunkers.base import BaseChunker, Chunk
from app.components.chunkers.factory import ChunkerFactory


class FixedChunker(BaseChunker):
    """Chunker that splits text into fixed-size chunks.

    Simple chunker that creates chunks of exactly the specified size
    (except possibly the last chunk). Useful when you need uniform
    chunk sizes.
    """

    name: str = "fixed"
    description: str = "Splits text into fixed-size chunks regardless of content boundaries"

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "chunk_size": {
                    "type": "integer",
                    "default": 512,
                    "description": "Exact size of each chunk in characters",
                    "minimum": 50,
                    "maximum": 8192,
                },
                "chunk_overlap": {
                    "type": "integer",
                    "default": 50,
                    "description": "Number of overlapping characters between chunks",
                    "minimum": 0,
                },
                "strip_whitespace": {
                    "type": "boolean",
                    "default": False,
                    "description": "Strip leading/trailing whitespace from chunks",
                },
            },
        }

    async def chunk(
        self,
        text: str,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        strip_whitespace: bool = False,
        **kwargs,
    ) -> List[Chunk]:
        """Split text into fixed-size chunks.

        Args:
            text: Text to split
            chunk_size: Size of each chunk
            chunk_overlap: Overlap between chunks
            strip_whitespace: Whether to strip whitespace

        Returns:
            List of Chunk objects
        """
        if not text:
            return []

        # Validate overlap
        if chunk_overlap >= chunk_size:
            chunk_overlap = chunk_size // 4

        chunks = []
        step = chunk_size - chunk_overlap
        start = 0
        index = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end]

            if strip_whitespace:
                chunk_text = chunk_text.strip()

            if chunk_text:
                chunks.append(
                    self._create_chunk(
                        content=chunk_text,
                        index=index,
                        start_char=start,
                        end_char=end,
                    )
                )
                index += 1

            start += step

        return chunks


# Register with factory
ChunkerFactory.register("fixed", FixedChunker)
