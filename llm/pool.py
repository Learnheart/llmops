"""Model Pool - Singleton quản lý tập trung các model instances."""

import threading
from pathlib import Path
from typing import Optional
from collections import OrderedDict

import yaml

from .models import LLMModel, EmbeddingModel


class ModelPool:
    """
    Singleton class quản lý tất cả LLM và Embedding model instances.

    Responsibilities:
    - Đọc config và validate
    - Cache loaded instances (tránh load trùng)
    - Memory management (LRU unload khi vượt limit)
    - Thread-safe khi concurrent access
    """

    _instance: Optional["ModelPool"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "ModelPool":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._config: dict = {}
        self._loaded_llm: OrderedDict[str, LLMModel] = OrderedDict()
        self._loaded_embedding: OrderedDict[str, EmbeddingModel] = OrderedDict()
        self._llm_locks: dict[str, threading.Lock] = {}
        self._embedding_locks: dict[str, threading.Lock] = {}

        self._load_config()

    def _load_config(self) -> None:
        """Load config từ file YAML."""
        config_path = Path(__file__).parent / "config.yaml"

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f)

        # Tạo locks cho mỗi model
        for name in self._config.get("models", {}).get("llm", {}):
            self._llm_locks[name] = threading.Lock()

        for name in self._config.get("models", {}).get("embedding", {}):
            self._embedding_locks[name] = threading.Lock()

    def reload_config(self) -> None:
        """Reload config từ file (useful khi thêm model mới)."""
        self._load_config()

    # ==================== LIST APIs ====================

    def list_llm_models(self) -> list[str]:
        """Trả về danh sách tên các LLM models available."""
        return list(self._config.get("models", {}).get("llm", {}).keys())

    def list_embedding_models(self) -> list[str]:
        """Trả về danh sách tên các Embedding models available."""
        return list(self._config.get("models", {}).get("embedding", {}).keys())

    # ==================== INFO APIs ====================

    def get_model_info(self, name: str) -> Optional[dict]:
        """
        Lấy thông tin chi tiết của model (cho Model Selector).

        Returns:
            dict với keys: path, tags, description, context_length, dimension, etc.
            None nếu model không tồn tại
        """
        # Tìm trong LLM
        llm_config = self._config.get("models", {}).get("llm", {}).get(name)
        if llm_config:
            return {"type": "llm", "name": name, **llm_config}

        # Tìm trong Embedding
        emb_config = self._config.get("models", {}).get("embedding", {}).get(name)
        if emb_config:
            return {"type": "embedding", "name": name, **emb_config}

        return None

    def get_llm_info(self, name: str) -> Optional[dict]:
        """Lấy thông tin LLM model."""
        config = self._config.get("models", {}).get("llm", {}).get(name)
        if config:
            return {"type": "llm", "name": name, **config}
        return None

    def get_embedding_info(self, name: str) -> Optional[dict]:
        """Lấy thông tin Embedding model."""
        config = self._config.get("models", {}).get("embedding", {}).get(name)
        if config:
            return {"type": "embedding", "name": name, **config}
        return None

    # ==================== GET INSTANCE APIs ====================

    def get_llm(self, name: Optional[str] = None) -> LLMModel:
        """
        Lấy LLM model instance (đã loaded).

        Args:
            name: Tên model. Nếu None, lấy default.

        Returns:
            LLMModel instance đã loaded và sẵn sàng sử dụng.

        Raises:
            ValueError: Nếu model name không tồn tại trong config.
        """
        if name is None:
            name = self._config.get("defaults", {}).get("llm")
            if name is None:
                raise ValueError("No default LLM configured")

        # Validate model exists
        model_config = self._config.get("models", {}).get("llm", {}).get(name)
        if model_config is None:
            available = self.list_llm_models()
            raise ValueError(f"LLM '{name}' not found. Available: {available}")

        # Check cache first (fast path)
        if name in self._loaded_llm:
            # Move to end (LRU update)
            self._loaded_llm.move_to_end(name)
            return self._loaded_llm[name]

        # Acquire lock for this specific model
        lock = self._llm_locks.get(name)
        if lock is None:
            lock = threading.Lock()
            self._llm_locks[name] = lock

        with lock:
            # Double-check after acquiring lock
            if name in self._loaded_llm:
                self._loaded_llm.move_to_end(name)
                return self._loaded_llm[name]

            # Check memory limit
            self._enforce_llm_limit()

            # Create and load model
            model = LLMModel(
                model_path=model_config["path"],
                model_type=model_config.get("model_type", "llama"),
                n_ctx=model_config.get("context_length", 2048),
                n_threads=model_config.get("n_threads", 2),
            )
            model.load()

            # Cache instance
            self._loaded_llm[name] = model

            return model

    def get_embedding(self, name: Optional[str] = None) -> EmbeddingModel:
        """
        Lấy Embedding model instance (đã loaded).

        Args:
            name: Tên model. Nếu None, lấy default.

        Returns:
            EmbeddingModel instance đã loaded và sẵn sàng sử dụng.

        Raises:
            ValueError: Nếu model name không tồn tại trong config.
        """
        if name is None:
            name = self._config.get("defaults", {}).get("embedding")
            if name is None:
                raise ValueError("No default embedding configured")

        # Validate model exists
        model_config = self._config.get("models", {}).get("embedding", {}).get(name)
        if model_config is None:
            available = self.list_embedding_models()
            raise ValueError(f"Embedding '{name}' not found. Available: {available}")

        # Check cache first (fast path)
        if name in self._loaded_embedding:
            self._loaded_embedding.move_to_end(name)
            return self._loaded_embedding[name]

        # Acquire lock for this specific model
        lock = self._embedding_locks.get(name)
        if lock is None:
            lock = threading.Lock()
            self._embedding_locks[name] = lock

        with lock:
            # Double-check after acquiring lock
            if name in self._loaded_embedding:
                self._loaded_embedding.move_to_end(name)
                return self._loaded_embedding[name]

            # Check memory limit
            self._enforce_embedding_limit()

            # Create and load model
            model = EmbeddingModel(model_path=model_config["path"])
            model.load()

            # Cache instance
            self._loaded_embedding[name] = model

            return model

    # ==================== MEMORY MANAGEMENT ====================

    def _enforce_llm_limit(self) -> None:
        """Unload LRU LLM model nếu vượt quá limit."""
        max_loaded = self._config.get("resource_limits", {}).get("max_loaded_llm", 2)

        while len(self._loaded_llm) >= max_loaded:
            # Pop oldest (LRU)
            oldest_name, oldest_model = self._loaded_llm.popitem(last=False)
            oldest_model.unload()

    def _enforce_embedding_limit(self) -> None:
        """Unload LRU Embedding model nếu vượt quá limit."""
        max_loaded = self._config.get("resource_limits", {}).get("max_loaded_embedding", 2)

        while len(self._loaded_embedding) >= max_loaded:
            oldest_name, oldest_model = self._loaded_embedding.popitem(last=False)
            oldest_model.unload()

    def release_llm(self, name: str) -> bool:
        """
        Manual release một LLM model khỏi cache.

        Returns:
            True nếu model đã được unload, False nếu model không trong cache.
        """
        if name in self._loaded_llm:
            model = self._loaded_llm.pop(name)
            model.unload()
            return True
        return False

    def release_embedding(self, name: str) -> bool:
        """
        Manual release một Embedding model khỏi cache.

        Returns:
            True nếu model đã được unload, False nếu model không trong cache.
        """
        if name in self._loaded_embedding:
            model = self._loaded_embedding.pop(name)
            model.unload()
            return True
        return False

    def release_all(self) -> None:
        """Unload tất cả models khỏi memory."""
        for model in self._loaded_llm.values():
            model.unload()
        self._loaded_llm.clear()

        for model in self._loaded_embedding.values():
            model.unload()
        self._loaded_embedding.clear()

    # ==================== STATUS APIs ====================

    def get_loaded_models(self) -> dict[str, list[str]]:
        """Trả về danh sách các models đang loaded trong memory."""
        return {
            "llm": list(self._loaded_llm.keys()),
            "embedding": list(self._loaded_embedding.keys()),
        }

    def is_loaded(self, name: str) -> bool:
        """Kiểm tra model đã loaded chưa."""
        return name in self._loaded_llm or name in self._loaded_embedding


# Global singleton instance
model_pool = ModelPool()
