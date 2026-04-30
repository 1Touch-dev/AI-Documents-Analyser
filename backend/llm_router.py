"""
LLM Router – unified multi-provider generation.

Supported providers:
  • "openai"   — GPT-4o, GPT-4.1, GPT-4.1-mini
  • "bedrock"  — ANY AWS Bedrock model via the Converse API

Provider is selected per-request via the `provider` argument.
No model allowlist for Bedrock – any model ID is accepted and passed straight
through to the Converse API.
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


class LLMRouter:
    """
    Unified LLM router dispatching to OpenAI or AWS Bedrock.

    Usage:
        await router.generate(
            model_name="amazon.nova-pro-v1:0",
            messages=[{"role": "user", "content": "Hello"}],
            provider="bedrock",
        )
    """

    async def close(self) -> None:
        return None

    # ── Model listing ─────────────────────────────────────────────────────────

    def list_models(self) -> list[str]:
        """Return OpenAI model names (backwards-compatible)."""
        return sorted(MODEL_REGISTRY.keys())

    def list_all_models(self) -> dict[str, Any]:
        """Return all models across providers."""
        from services.bedrock_service import BedrockService
        openai_models = [
            {"model_id": k, "label": k, "provider": "OpenAI"}
            for k in sorted(MODEL_REGISTRY.keys())
        ]
        bedrock_models = BedrockService.get_default_models()
        return {
            "openai":  openai_models,
            "bedrock": bedrock_models,
            "all":     openai_models + bedrock_models,
        }

    # ── OpenAI model resolution ───────────────────────────────────────────────

    def resolve_model(
        self,
        model_name: str,
        query: str = "",
        api_keys: dict[str, str | None] | None = None,
    ) -> str:
        """Resolve an OpenAI model name (auto-routing, legacy alias support)."""
        requested = (model_name or "auto").strip()
        if requested == "auto":
            return "gpt-4.1" if _is_complex_query(query) else "gpt-4o"
        if requested in MODEL_REGISTRY:
            return requested
        if requested in LEGACY_MODEL_ALIASES:
            mapped = LEGACY_MODEL_ALIASES[requested]
            logger.info("Mapped legacy model '%s' → '%s'.", requested, mapped)
            return mapped
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
        provider: str = "openai",
    ) -> str:
        """
        Generate a response from the specified provider.

        Args:
            model_name:  Any valid model name.
                         For OpenAI: "gpt-4o", "gpt-4.1", "auto", legacy names.
                         For Bedrock: ANY Bedrock model ID (no allowlist).
            messages:    OpenAI-style [{role, content}, …] list.
            temperature: Sampling temperature.
            max_tokens:  Max output tokens.
            api_keys:    Optional per-request key overrides (OpenAI only).
            provider:    "openai" (default) | "bedrock" | "aws" | "aws-bedrock".

        Returns:
            Generated text string.
        """
        if _is_bedrock_provider(provider):
            # Use settings default when caller passes empty/None model
            bedrock_model = (model_name or "").strip() or settings.bedrock_default_model
            return await self._call_bedrock(bedrock_model, messages, temperature, max_tokens)
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
        model_id: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """
        Route to Bedrock Converse API.
        model_id is passed through without validation – any Bedrock model works.
        """
        from services.bedrock_service import get_bedrock_service
        svc = get_bedrock_service()
        logger.info("Bedrock call: model_id=%s", model_id)
        return await svc.generate_from_messages(
            messages=messages,
            model_id=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
        )


# ── Helper ────────────────────────────────────────────────────────────────────

def _is_bedrock_provider(provider: str | None) -> bool:
    return (provider or "").lower().strip() in ("bedrock", "aws", "aws-bedrock", "amazon")
