"""Base chunker class for text chunking."""

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.components.base.component import BaseComponent


@dataclass
class Chunk:
    """A text chunk from a document."""

    content: str
    """The text content of the chunk."""

    index: int
    """Position of this chunk in the document (0-indexed)."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata for this chunk."""

    start_char: Optional[int] = None
    """Starting character position in original document."""

    end_char: Optional[int] = None
    """Ending character position in original document."""

    def __len__(self) -> int:
        return len(self.content)

    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary."""
        return {
            "content": self.content,
            "index": self.index,
            "metadata": self.metadata,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "length": len(self.content),
        }


class BaseChunker(BaseComponent):
    """Abstract base class for text chunkers.

    Chunkers split text into smaller, semantically meaningful chunks
    for embedding and retrieval.
    """

    category: str = "chunkers"

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Return configuration schema for chunker."""
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
            },
            "required": ["chunk_size"],
        }

    @abstractmethod
    async def chunk(
        self,
        text: str,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        **kwargs,
    ) -> List[Chunk]:
        """Split text into chunks.

        Args:
            text: Text to split into chunks
            chunk_size: Target size for each chunk in characters
            chunk_overlap: Number of overlapping characters between chunks
            **kwargs: Additional chunker-specific options

        Returns:
            List of Chunk objects
        """
        pass

    async def process(
        self,
        input_data: Any,
        config: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        """Process method implementing BaseComponent interface.

        Args:
            input_data: Text string to chunk
            config: Chunker configuration options

        Returns:
            List of Chunk objects
        """
        if not isinstance(input_data, str):
            raise ValueError("Input must be a string")

        config = config or {}
        return await self.chunk(input_data, **config)

    def _create_chunk(
        self,
        content: str,
        index: int,
        start_char: Optional[int] = None,
        end_char: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Chunk:
        """Helper to create a Chunk object.

        Args:
            content: Chunk text content
            index: Chunk index
            start_char: Starting position in original text
            end_char: Ending position in original text
            metadata: Additional metadata

        Returns:
            Chunk object
        """
        return Chunk(
            content=content,
            index=index,
            start_char=start_char,
            end_char=end_char,
            metadata=metadata or {},
        )
