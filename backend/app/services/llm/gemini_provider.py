"""Google Gemini provider."""
from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.services.llm.base import LLMProvider


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self) -> None:
        settings = get_settings()
        import google.generativeai as genai

        genai.configure(api_key=settings.gemini_api_key)
        self.model_name = settings.gemini_model
        self._genai = genai

    async def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> str:
        model = self._genai.GenerativeModel(
            self.model_name,
            system_instruction=system,
        )

        def _run() -> str:
            result = model.generate_content(
                user,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                    "response_mime_type": "application/json",
                },
            )
            return result.text or "{}"

        return await asyncio.to_thread(_run)
