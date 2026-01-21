"""Adapter factory and base interface."""

from abc import ABC, abstractmethod
from typing import Iterator
from schema.rag import RemoteFile


class BaseAdapter(ABC):
    """Base interface cho source adapters"""

    source_type: str

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def list_files(self, include_patterns: list[str], exclude_patterns: list[str]) -> Iterator[RemoteFile]:
        pass

    @abstractmethod
    def download_file(self, remote_file: RemoteFile) -> bytes:
        pass


# Registry
_ADAPTERS: dict[str, type[BaseAdapter]] = {}


def register_adapter(source_type: str):
    """Decorator để register adapter"""
    def decorator(cls: type[BaseAdapter]):
        _ADAPTERS[source_type] = cls
        return cls
    return decorator


def get_adapter(source_type: str, config: dict) -> BaseAdapter:
    """Factory để tạo adapter"""
    if source_type not in _ADAPTERS:
        raise ValueError(f"Unknown source type: {source_type}")
    return _ADAPTERS[source_type](config)


# Import adapters để trigger registration
from rag.adapters import github_adapter  # noqa: E402, F401
