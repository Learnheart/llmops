"""LLM service - handles LLM provider integrations."""

from enum import Enum
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod

from app.config import get_settings


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"


class LLMError(Exception):
    """Base exception for LLM errors."""
    pass


class LLMProviderNotConfiguredError(LLMError):
    """Raised when LLM provider is not configured."""

    def __init__(self, provider: str):
        self.provider = provider
        super().__init__(f"LLM provider '{provider}' is not configured")


class LLMAPIError(LLMError):
    """Raised when LLM API call fails."""

    def __init__(self, provider: str, message: str):
        self.provider = provider
        super().__init__(f"LLM API error ({provider}): {message}")


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        """Generate text from prompt."""
        pass

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        """Chat completion with messages."""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI API client."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        """Generate text using OpenAI."""
        try:
            response = await self.client.chat.completions.create(
                model=model or "gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise LLMAPIError("openai", str(e))

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        """Chat completion using OpenAI."""
        try:
            response = await self.client.chat.completions.create(
                model=model or "gpt-4o-mini",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise LLMAPIError("openai", str(e))


class AnthropicClient(BaseLLMClient):
    """Anthropic API client."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        """Generate text using Anthropic."""
        try:
            response = await self.client.messages.create(
                model=model or "claude-3-haiku-20240307",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
                **kwargs,
            )
            return response.content[0].text if response.content else ""
        except Exception as e:
            raise LLMAPIError("anthropic", str(e))

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        """Chat completion using Anthropic."""
        try:
            # Convert messages to Anthropic format
            anthropic_messages = []
            system_message = None

            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    anthropic_messages.append({
                        "role": msg["role"],
                        "content": msg["content"],
                    })

            create_kwargs = {
                "model": model or "claude-3-haiku-20240307",
                "max_tokens": max_tokens,
                "messages": anthropic_messages,
                **kwargs,
            }

            if system_message:
                create_kwargs["system"] = system_message

            response = await self.client.messages.create(**create_kwargs)
            return response.content[0].text if response.content else ""
        except Exception as e:
            raise LLMAPIError("anthropic", str(e))


class GroqClient(BaseLLMClient):
    """Groq API client - uses OpenAI-compatible API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url="https://api.groq.com/openai/v1",
            )
        return self._client

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        """Generate text using Groq."""
        try:
            response = await self.client.chat.completions.create(
                model=model or "llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise LLMAPIError("groq", str(e))

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        """Chat completion using Groq."""
        try:
            response = await self.client.chat.completions.create(
                model=model or "llama-3.3-70b-versatile",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise LLMAPIError("groq", str(e))


class LLMService:
    """Service for LLM operations.

    Supports multiple providers (OpenAI, Anthropic, Groq) with fallback.
    """

    def __init__(self):
        self.settings = get_settings()
        self._clients: Dict[LLMProvider, BaseLLMClient] = {}

    def _get_client(self, provider: LLMProvider) -> BaseLLMClient:
        """Get or create client for provider."""
        if provider in self._clients:
            return self._clients[provider]

        if provider == LLMProvider.OPENAI:
            if not self.settings.openai_api_key:
                raise LLMProviderNotConfiguredError("openai")
            self._clients[provider] = OpenAIClient(self.settings.openai_api_key)
        elif provider == LLMProvider.ANTHROPIC:
            if not self.settings.anthropic_api_key:
                raise LLMProviderNotConfiguredError("anthropic")
            self._clients[provider] = AnthropicClient(self.settings.anthropic_api_key)
        elif provider == LLMProvider.GROQ:
            if not self.settings.groq_api_key:
                raise LLMProviderNotConfiguredError("groq")
            self._clients[provider] = GroqClient(self.settings.groq_api_key)
        else:
            raise LLMProviderNotConfiguredError(provider)

        return self._clients[provider]

    def _get_default_provider(self) -> LLMProvider:
        """Get default provider from settings."""
        provider_str = self.settings.default_llm_provider.lower()
        if provider_str == "anthropic":
            return LLMProvider.ANTHROPIC
        elif provider_str == "groq":
            return LLMProvider.GROQ
        return LLMProvider.OPENAI

    async def generate(
        self,
        prompt: str,
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        """Generate text using specified or default provider.

        Args:
            prompt: The prompt text
            provider: LLM provider to use (defaults to settings)
            model: Model to use (defaults to provider's default)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text

        Raises:
            LLMProviderNotConfiguredError: If provider not configured
            LLMAPIError: If API call fails
        """
        provider = provider or self._get_default_provider()
        client = self._get_client(provider)
        return await client.generate(
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    async def chat(
        self,
        messages: List[Dict[str, str]],
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        """Chat completion using specified or default provider.

        Args:
            messages: List of message dicts with 'role' and 'content'
            provider: LLM provider to use (defaults to settings)
            model: Model to use (defaults to provider's default)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated response text

        Raises:
            LLMProviderNotConfiguredError: If provider not configured
            LLMAPIError: If API call fails
        """
        provider = provider or self._get_default_provider()
        client = self._get_client(provider)
        return await client.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    def is_provider_configured(self, provider: LLMProvider) -> bool:
        """Check if a provider is configured."""
        if provider == LLMProvider.OPENAI:
            return bool(self.settings.openai_api_key)
        elif provider == LLMProvider.ANTHROPIC:
            return bool(self.settings.anthropic_api_key)
        elif provider == LLMProvider.GROQ:
            return bool(self.settings.groq_api_key)
        return False

    def get_configured_providers(self) -> List[LLMProvider]:
        """Get list of configured providers."""
        return [p for p in LLMProvider if self.is_provider_configured(p)]
