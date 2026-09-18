"""Resolve LLM provider from settings."""
from __future__ import annotations

from app.core.config import get_settings
from app.services.llm.base import LLMProvider
from app.services.llm.mock_provider import MockLLMProvider


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    provider = (settings.llm_provider or "mock").lower()

    if provider == "openai" and settings.openai_api_key:
        from app.services.llm.openai_provider import OpenAIProvider

        return OpenAIProvider()
    if provider == "gemini" and settings.gemini_api_key:
        from app.services.llm.gemini_provider import GeminiProvider

        return GeminiProvider()
    if provider == "anthropic" and settings.anthropic_api_key:
        from app.services.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider()

    # Auto-detect if keys present but provider left as mock
    if settings.openai_api_key and provider != "mock":
        from app.services.llm.openai_provider import OpenAIProvider

        return OpenAIProvider()

    return MockLLMProvider()
