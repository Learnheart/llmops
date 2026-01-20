"""Recursive character text chunker."""

from typing import Any, Dict, List, Optional

from app.components.chunkers.base import BaseChunker, Chunk
from app.components.chunkers.factory import ChunkerFactory


class RecursiveChunker(BaseChunker):
    """Chunker that recursively splits text using a hierarchy of separators.

    This is the most commonly used chunker. It tries to split text at
    natural boundaries (paragraphs, sentences, words) while respecting
    the chunk size limit.
    """

    name: str = "recursive"
    description: str = "Recursively splits text using paragraph, sentence, and word boundaries"

    DEFAULT_SEPARATORS = [
        "\n\n",  # Paragraphs
        "\n",    # Lines
        ". ",    # Sentences
        "? ",    # Questions
        "! ",    # Exclamations
        "; ",    # Semicolons
        ", ",    # Commas
        " ",     # Words
        "",      # Characters (last resort)
    ]

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
                    "default": 50,
                    "description": "Number of overlapping characters between chunks",
                    "minimum": 0,
                },
                "separators": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of separators to try in order",
                },
                "keep_separator": {
                    "type": "boolean",
                    "default": True,
                    "description": "Keep separator in the chunks",
                },
            },
        }

    async def chunk(
        self,
        text: str,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        separators: Optional[List[str]] = None,
        keep_separator: bool = True,
        **kwargs,
    ) -> List[Chunk]:
        """Split text recursively using separators.

        Args:
            text: Text to split
            chunk_size: Target chunk size
            chunk_overlap: Overlap between chunks
            separators: List of separators to try
            keep_separator: Whether to keep separator in chunks

        Returns:
            List of Chunk objects
        """
        if not text:
            return []

        if separators is None:
            separators = self.DEFAULT_SEPARATORS.copy()

        # Get initial splits
        splits = self._split_text(
            text=text,
            separators=separators,
            chunk_size=chunk_size,
            keep_separator=keep_separator,
        )

        # Merge splits into chunks with overlap
        chunks = self._merge_splits(
            splits=splits,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        # Create Chunk objects with positions
        result = []
        current_pos = 0

        for i, chunk_text in enumerate(chunks):
            # Find position in original text
            try:
                start = text.index(chunk_text[:50], current_pos) if len(chunk_text) >= 50 else text.index(chunk_text, current_pos)
            except ValueError:
                start = current_pos

            result.append(
                self._create_chunk(
                    content=chunk_text,
                    index=i,
                    start_char=start,
                    end_char=start + len(chunk_text),
                )
            )
            current_pos = start + len(chunk_text) - chunk_overlap

        return result

    def _split_text(
        self,
        text: str,
        separators: List[str],
        chunk_size: int,
        keep_separator: bool,
    ) -> List[str]:
        """Recursively split text using separators."""
        final_splits = []

        # Find the best separator
        separator = ""
        for sep in separators:
            if sep == "":
                separator = sep
                break
            if sep in text:
                separator = sep
                break

        # Split the text
        if separator:
            splits = text.split(separator)
        else:
            splits = list(text)

        # Process splits
        for i, split in enumerate(splits):
            # Add separator back if needed
            if keep_separator and separator and i < len(splits) - 1:
                split = split + separator

            if len(split) <= chunk_size:
                if split.strip():
                    final_splits.append(split)
            else:
                # Need to split further
                if separator:
                    remaining_separators = separators[separators.index(separator) + 1:]
                else:
                    remaining_separators = []

                if remaining_separators:
                    sub_splits = self._split_text(
                        text=split,
                        separators=remaining_separators,
                        chunk_size=chunk_size,
                        keep_separator=keep_separator,
                    )
                    final_splits.extend(sub_splits)
                else:
                    # No more separators, force split by chunk_size
                    for j in range(0, len(split), chunk_size):
                        part = split[j:j + chunk_size]
                        if part.strip():
                            final_splits.append(part)

        return final_splits

    def _merge_splits(
        self,
        splits: List[str],
        chunk_size: int,
        chunk_overlap: int,
    ) -> List[str]:
        """Merge small splits into larger chunks."""
        if not splits:
            return []

        chunks = []
        current_chunk = []
        current_length = 0

        for split in splits:
            split_length = len(split)

            # If adding this split would exceed chunk_size, finalize current chunk
            if current_length + split_length > chunk_size and current_chunk:
                chunks.append("".join(current_chunk))

                # Start new chunk with overlap
                if chunk_overlap > 0:
                    overlap_text = "".join(current_chunk)
                    overlap_start = max(0, len(overlap_text) - chunk_overlap)
                    current_chunk = [overlap_text[overlap_start:]]
                    current_length = len(current_chunk[0])
                else:
                    current_chunk = []
                    current_length = 0

            current_chunk.append(split)
            current_length += split_length

        # Add final chunk
        if current_chunk:
            chunks.append("".join(current_chunk))

        return chunks


# Register with factory
ChunkerFactory.register("recursive", RecursiveChunker)
