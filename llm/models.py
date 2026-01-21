"""LLM and Embedding model wrappers."""

from dataclasses import dataclass
from typing import Optional, Any
from sentence_transformers import SentenceTransformer

# Try llama-cpp-python first, fallback to ctransformers
try:
    from llama_cpp import Llama
    BACKEND = "llama_cpp"
except ImportError:
    from ctransformers import AutoModelForCausalLM
    BACKEND = "ctransformers"


@dataclass
class ChatMessage:
    """Chat message structure."""
    role: str  # "system", "user", "assistant"
    content: str


class LLMModel:
    """LLM model wrapper for text generation."""

    def __init__(
        self,
        model_path: str,
        model_type: str = "llama",
        n_ctx: int = 2048,
        n_threads: int = 2,
    ):
        self._model: Optional[Any] = None
        self._model_path = model_path
        self._model_type = model_type
        self._n_ctx = n_ctx
        self._n_threads = n_threads
        self._backend = BACKEND

    def load(self) -> None:
        """Load model into memory."""
        if self._model is not None:
            return

        if self._backend == "llama_cpp":
            self._model = Llama(
                model_path=self._model_path,
                n_ctx=self._n_ctx,
                n_threads=self._n_threads,
                verbose=False,
            )
        else:
            self._model = AutoModelForCausalLM.from_pretrained(
                self._model_path,
                model_type=self._model_type,
                context_length=self._n_ctx,
                threads=self._n_threads,
            )

    def unload(self) -> None:
        """Unload model from memory."""
        self._model = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def backend(self) -> str:
        return self._backend

    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> str:
        """Generate text from prompt."""
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        if self._backend == "llama_cpp":
            response = self._model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                echo=False,
            )
            return response["choices"][0]["text"]
        else:
            return self._model(
                prompt,
                max_new_tokens=max_tokens,
                temperature=temperature,
            )

    def chat(
        self,
        messages: list[ChatMessage],
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> str:
        """Generate chat completion."""
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        if self._backend == "llama_cpp":
            formatted_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            response = self._model.create_chat_completion(
                messages=formatted_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            )
            return response["choices"][0]["message"]["content"]
        else:
            # ctransformers doesn't have chat API, format manually
            prompt = self._format_chat_prompt(messages)
            return self.generate(prompt, max_tokens, temperature)

    def _format_chat_prompt(self, messages: list[ChatMessage]) -> str:
        """Format messages into a prompt string."""
        parts = []
        for msg in messages:
            if msg.role == "system":
                parts.append(f"System: {msg.content}")
            elif msg.role == "user":
                parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                parts.append(f"Assistant: {msg.content}")
        parts.append("Assistant:")
        return "\n".join(parts)


class EmbeddingModel:
    """Embedding model wrapper for text vectorization."""

    def __init__(self, model_path: str):
        self._model: Optional[SentenceTransformer] = None
        self._model_path = model_path
        self._dimension: Optional[int] = None

    def load(self) -> None:
        """Load model into memory."""
        if self._model is None:
            self._model = SentenceTransformer(self._model_path)
            self._dimension = self._model.get_sentence_embedding_dimension()

    def unload(self) -> None:
        """Unload model from memory."""
        self._model = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def dimension(self) -> Optional[int]:
        """Return embedding dimension."""
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for texts."""
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        return self._model.encode(texts).tolist()

    def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        return self.embed([text])[0]
