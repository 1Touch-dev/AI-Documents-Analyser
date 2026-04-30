"""
LLM Router – unified multi-provider generation.

Supported providers:
  • openai   — GPT-4o, GPT-4.1, GPT-4.1-mini (default)
  • bedrock  — All AWS Bedrock models via the converse API
                (Claude Opus/Sonnet/Haiku, Amazon Nova, Llama 3, Mistral, Cohere)
"""

from __future__ import annotations

import logging
from typing import Any

from config.settings import settings

logger = logging.getLogger(__name__)


# ── OpenAI model registry ─────────────────────────────────────────────────────

MODEL_REGISTRY: dict[str, str] = {
    "gpt-4o":       "gpt-4o",
    "gpt-4.1":      "gpt-4.1",
    "gpt-4.1-mini": "gpt-4.1-mini",
}

LEGACY_MODEL_ALIASES: dict[str, str] = {
    "llama3.2":         "gpt-4o",
    "tinyllama":        "gpt-4o",
    "llama3":           "gpt-4o",
    "llama3.1":         "gpt-4o",
    "mistral":          "gpt-4o",
    "mixtral":          "gpt-4o",
    "gemma":            "gpt-4o",
    "gemma2":           "gpt-4o",
    "claude-3.5-sonnet":"gpt-4o",
    "claude-4.6-opus":  "gpt-4.1",
    "claude-4.6-sonnet":"gpt-4.1",
    "gemini-3.1-pro":   "gpt-4.1",
    "gemini-3-flash":   "gpt-4o",
    "gemini-3.1-flash": "gpt-4o",
    "gpt-5.4":          "gpt-4.1",
    "o3-mini":          "gpt-4o",
}

_COMPLEX_KEYWORDS = {
    "analyze", "compare", "evaluate", "synthesize", "strategy",
    "recommend", "design", "architecture", "complex", "detailed",
    "comprehensive", "multi-step", "reasoning", "explain why",
}


def _is_complex_query(query: str) -> bool:
    q = query.lower()
    if len(query) > 300:
        return True
    return any(kw in q for kw in _COMPLEX_KEYWORDS)


# ── Provider helpers ──────────────────────────────────────────────────────────

def _is_bedrock_model(model_name: str) -> bool:
    """Return True if the model name belongs to the Bedrock registry."""
    from services.bedrock_service import BEDROCK_MODELS
    return model_name in BEDROCK_MODELS


def _resolve_provider(provider: str | None, model_name: str) -> str:
    """
    Determine the effective provider.
    If provider is explicitly set, honour it.
    Otherwise auto-detect from the model name.
    """
    if provider and provider.lower() in ("bedrock", "aws", "aws-bedrock"):
        return "bedrock"
    if provider and provider.lower() == "openai":
        return "openai"
    # Auto-detect: if model is in Bedrock registry → bedrock, else → openai
    if _is_bedrock_model(model_name):
        return "bedrock"
    return "openai"


# ── Main Router class ─────────────────────────────────────────────────────────

class LLMRouter:
    """
    Unified LLM router.  A single `generate()` call dispatches to the
    correct provider based on the `provider` argument or model name.
    """

    async def close(self) -> None:
        return None

    # ── Model listing ─────────────────────────────────────────────────────────

    def list_models(self) -> list[str]:
        """Return all OpenAI model names (legacy compatibility)."""
        return sorted(MODEL_REGISTRY.keys())

    def list_all_models(self) -> dict[str, Any]:
        """Return all available models across all providers."""
        from services.bedrock_service import BEDROCK_MODELS, _infer_provider
        openai_models = [
            {"name": k, "model_id": k, "provider": "OpenAI"}
            for k in sorted(MODEL_REGISTRY.keys())
        ]
        bedrock_models = [
            {"name": k, "model_id": v, "provider": _infer_provider(k)}
            for k, v in BEDROCK_MODELS.items()
        ]
        return {
            "openai":  openai_models,
            "bedrock": bedrock_models,
            "all":     openai_models + bedrock_models,
        }

    # ── Model resolution ──────────────────────────────────────────────────────

    def resolve_model(
        self,
        model_name: str,
        query: str = "",
        api_keys: dict[str, str | None] | None = None,
    ) -> str:
        """Resolve an OpenAI model name (for backwards-compatible callers)."""
        requested = (model_name or "auto").strip()
        if requested == "auto":
            return "gpt-4.1" if _is_complex_query(query) else "gpt-4o"
        if requested in MODEL_REGISTRY:
            return requested
        if requested in LEGACY_MODEL_ALIASES:
            mapped = LEGACY_MODEL_ALIASES[requested]
            logger.info("Mapped legacy model '%s' to '%s'.", requested, mapped)
            return mapped
        # Bedrock model names fall through here — caller should use generate() with provider
        logger.warning("Unknown OpenAI model '%s'; defaulting to gpt-4o.", requested)
        return "gpt-4o"

    # ── Main generation entrypoint ────────────────────────────────────────────

    async def generate(
        self,
        model_name: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        api_keys: dict[str, str | None] | None = None,
        provider: str | None = None,
    ) -> str:
        """
        Generate a response.

        Args:
            model_name:  Friendly model name (e.g. "gpt-4o", "claude-sonnet-4.6", "nova-pro").
            messages:    OpenAI-style message list [{role, content}, …].
            temperature: Sampling temperature.
            max_tokens:  Max output tokens.
            api_keys:    Optional per-request API key overrides.
            provider:    "openai" | "bedrock". Auto-detected if omitted.

        Returns:
            Generated text string.
        """
        effective_provider = _resolve_provider(provider, model_name)

        if effective_provider == "bedrock":
            return await self._call_bedrock(model_name, messages, temperature, max_tokens)
        else:
            resolved = self.resolve_model(model_name, "", api_keys)
            return await self._call_openai(resolved, messages, temperature, max_tokens, api_keys)

    # ── OpenAI backend ────────────────────────────────────────────────────────

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

    # ── Bedrock backend ───────────────────────────────────────────────────────

    async def _call_bedrock(
        self,
        model_name: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        from services.bedrock_service import get_bedrock_service
        svc = get_bedrock_service()
        return await svc.generate_from_messages(
            messages=messages,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )
