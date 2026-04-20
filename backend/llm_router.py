"""
LLM Router – routes all generation through OpenAI GPT API models.
"""

from __future__ import annotations

import logging
from typing import Any

from config.settings import settings

logger = logging.getLogger(__name__)


MODEL_REGISTRY: dict[str, str] = {
    "gpt-4o": "gpt-4o",
    "gpt-4.1": "gpt-4.1",
    "gpt-4.1-mini": "gpt-4.1-mini",
}

# Map previously supported non-GPT or local model selections back to GPT.
LEGACY_MODEL_ALIASES = {
    "llama3.2": "gpt-4o",
    "tinyllama": "gpt-4o",
    "llama3": "gpt-4o",
    "llama3.1": "gpt-4o",
    "mistral": "gpt-4o",
    "mixtral": "gpt-4o",
    "gemma": "gpt-4o",
    "gemma2": "gpt-4o",
    "claude-3.5-sonnet": "gpt-4o",
    "claude-4.6-opus": "gpt-4.1",
    "claude-4.6-sonnet": "gpt-4.1",
    "gemini-3.1-pro": "gpt-4.1",
    "gemini-3-flash": "gpt-4o",
    "gemini-3.1-flash": "gpt-4o",
    "gpt-5.4": "gpt-4.1",
    "o3-mini": "gpt-4o",
}

_COMPLEX_KEYWORDS = {
    "analyze",
    "compare",
    "evaluate",
    "synthesize",
    "strategy",
    "recommend",
    "design",
    "architecture",
    "complex",
    "detailed",
    "comprehensive",
    "multi-step",
    "reasoning",
    "explain why",
}


def _is_complex_query(query: str) -> bool:
    q = query.lower()
    if len(query) > 300:
        return True
    return any(kw in q for kw in _COMPLEX_KEYWORDS)


class LLMRouter:
    """Route all generation through OpenAI GPT chat models."""

    async def close(self) -> None:
        return None

    def list_models(self) -> list[str]:
        return sorted(MODEL_REGISTRY.keys())

    def resolve_model(
        self,
        model_name: str,
        query: str = "",
        api_keys: dict[str, str | None] | None = None,
    ) -> str:
        requested = (model_name or "auto").strip()
        if requested == "auto":
            return "gpt-4.1" if _is_complex_query(query) else "gpt-4o"
        if requested in MODEL_REGISTRY:
            return requested
        if requested in LEGACY_MODEL_ALIASES:
            mapped = LEGACY_MODEL_ALIASES[requested]
            logger.info("Mapped legacy model '%s' to '%s'.", requested, mapped)
            return mapped
        logger.warning("Unknown model '%s'; defaulting to gpt-4o.", requested)
        return "gpt-4o"

    async def generate(
        self,
        model_name: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        api_keys: dict[str, str | None] | None = None,
    ) -> str:
        resolved_model = self.resolve_model(model_name)
        return await self._call_openai(
            resolved_model,
            messages,
            temperature,
            max_tokens,
            api_keys,
        )

    async def _call_openai(
        self,
        model_id: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        api_keys: dict[str, str | None] | None,
    ) -> str:
        from openai import AsyncOpenAI

        keys = api_keys or {}
        api_key = keys.get("openai_api_key") or settings.openai_api_key
        if not api_key:
            raise ValueError(
                "OpenAI API key missing. Set OPENAI_API_KEY or provide it in the UI."
            )

        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""
