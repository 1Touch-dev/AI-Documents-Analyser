"""
LLM Router – routes queries to cloud API language models.

Supports:
  • OpenAI  (GPT-4o, GPT-4o-mini, o3-mini)
  • Anthropic (Claude 4.6 Opus, Claude 4.6 Sonnet, Claude 3.5 Sonnet)
  • Google Gemini (Gemini 2.5 Pro, Gemini 2.0 Flash)

Default model: gpt-4o (used when model="auto" and no key preference set).
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, AsyncIterator

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────
# Supported models (API only)
# ─────────────────────────────────────────────────────────
class ModelProvider(str, Enum):
    OPENAI    = "openai"
    ANTHROPIC = "anthropic"
    GEMINI    = "gemini"


MODEL_REGISTRY: dict[str, dict[str, Any]] = {
    # ── OpenAI ────────────────────────────────────────────
    "gpt-4o":       {"provider": ModelProvider.OPENAI,    "model_id": "gpt-4o"},
    "gpt-4o-mini":  {"provider": ModelProvider.OPENAI,    "model_id": "gpt-4o-mini"},
    "o3-mini":      {"provider": ModelProvider.OPENAI,    "model_id": "o3-mini"},
    # ── Anthropic ─────────────────────────────────────────
    "claude-4.6-opus":   {"provider": ModelProvider.ANTHROPIC, "model_id": "claude-opus-4-5"},
    "claude-4.6-sonnet": {"provider": ModelProvider.ANTHROPIC, "model_id": "claude-sonnet-4-5"},
    "claude-3.5-sonnet": {"provider": ModelProvider.ANTHROPIC, "model_id": "claude-3-5-sonnet-20241022"},
    # ── Gemini ────────────────────────────────────────────
    "gemini-2.5-pro":   {"provider": ModelProvider.GEMINI, "model_id": "gemini-2.5-pro-preview-05-06"},
    "gemini-2.0-flash": {"provider": ModelProvider.GEMINI, "model_id": "gemini-2.0-flash"},
}

DEFAULT_MODEL = "gpt-4o"


def resolve_model(
    model_name: str,
    api_keys: dict[str, str | None] | None = None,
) -> str:
    """
    Resolve 'auto' to a concrete model based on which API keys are configured.
    Priority: OpenAI → Anthropic → Gemini.
    """
    if model_name != "auto" and model_name in MODEL_REGISTRY:
        return model_name
    keys = api_keys or {}
    if keys.get("openai_api_key") or settings.openai_api_key:
        return "gpt-4o"
    if keys.get("anthropic_api_key") or settings.anthropic_api_key:
        return "claude-4.6-sonnet"
    if keys.get("gemini_api_key"):
        return "gemini-2.5-pro"
    return DEFAULT_MODEL


# ─────────────────────────────────────────────────────────
# Router class
# ─────────────────────────────────────────────────────────
class LLMRouter:
    """Route queries to the correct cloud LLM backend."""

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(timeout=120.0)

    async def close(self) -> None:
        await self._http.aclose()

    def list_models(self) -> list[str]:
        return sorted(MODEL_REGISTRY.keys())

    def resolve_model(
        self,
        model_name: str,
        query: str = "",
        api_keys: dict[str, str | None] | None = None,
        force_local: bool = False,
    ) -> str:
        return resolve_model(model_name, api_keys)

    async def generate_with_fallback(
        self,
        preferred_model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        api_keys: dict[str, str | None] | None = None,
    ) -> tuple[str, str]:
        """Try preferred_model; fall back down the registry list on errors."""
        fallback_chain = [preferred_model] + [m for m in MODEL_REGISTRY if m != preferred_model]
        last_err: Exception | None = None
        for model in fallback_chain:
            try:
                answer = await self.generate(model, messages, temperature, max_tokens, api_keys)
                return answer, model
            except Exception as exc:
                logger.warning("Model %s failed (%s), trying next fallback.", model, exc)
                last_err = exc
        raise RuntimeError(f"All models failed. Last error: {last_err}")

    async def generate(
        self,
        model_name: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        api_keys: dict[str, str | None] | None = None,
    ) -> str:
        info = MODEL_REGISTRY.get(model_name)
        if not info:
            raise ValueError(f"Unknown model: {model_name}. Available: {self.list_models()}")
        provider = info["provider"]
        model_id  = info["model_id"]
        if provider == ModelProvider.OPENAI:
            return await self._call_openai(model_id, messages, temperature, max_tokens, api_keys)
        elif provider == ModelProvider.ANTHROPIC:
            return await self._call_anthropic(model_id, messages, temperature, max_tokens, api_keys)
        elif provider == ModelProvider.GEMINI:
            return await self._call_gemini(model_id, messages, temperature, max_tokens, api_keys)
        raise ValueError(f"Unsupported provider: {provider}")

    # ── OpenAI ───────────────────────────────────────────
    async def _call_openai(
        self, model_id: str, messages: list[dict], temperature: float, max_tokens: int, api_keys: dict | None
    ) -> str:
        from openai import AsyncOpenAI
        keys = api_keys or {}
        api_key = keys.get("openai_api_key") or settings.openai_api_key
        if not api_key:
            raise ValueError("OpenAI API key missing. Please provide it in the UI settings.")
        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model=model_id, messages=messages,
            temperature=temperature, max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    # ── Anthropic ────────────────────────────────────────
    async def _call_anthropic(
        self, model_id: str, messages: list[dict], temperature: float, max_tokens: int, api_keys: dict | None
    ) -> str:
        from anthropic import AsyncAnthropic
        keys = api_keys or {}
        api_key = keys.get("anthropic_api_key") or settings.anthropic_api_key
        if not api_key:
            raise ValueError("Anthropic API key missing. Please provide it in the UI settings.")
        client = AsyncAnthropic(api_key=api_key)
        system_msg = ""
        anthropic_messages = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                anthropic_messages.append({"role": m["role"], "content": m["content"]})
        response = await client.messages.create(
            model=model_id, max_tokens=max_tokens, temperature=temperature,
            system=system_msg, messages=anthropic_messages,
        )
        return response.content[0].text if response.content else ""

    # ── Gemini ───────────────────────────────────────────
    async def _call_gemini(
        self, model_id: str, messages: list[dict], temperature: float, max_tokens: int, api_keys: dict | None
    ) -> str:
        keys = api_keys or {}
        api_key = keys.get("gemini_api_key")
        if not api_key:
            raise ValueError("Gemini API key missing. Please provide it in the UI.")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
        gemini_messages, system_parts = [], []
        for m in messages:
            if m["role"] == "system":
                system_parts.append(m["content"])
            else:
                gemini_messages.append({
                    "role": "user" if m["role"] == "user" else "model",
                    "parts": [{"text": m["content"]}],
                })
        payload: dict[str, Any] = {
            "contents": gemini_messages,
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }
        if system_parts:
            payload["systemInstruction"] = {"parts": [{"text": "\n".join(system_parts)}]}
        resp = await self._http.post(url, json=payload, headers={"Content-Type": "application/json"})
        if resp.status_code == 404:
            url = f"https://generativelanguage.googleapis.com/v1/models/{model_id}:generateContent?key={api_key}"
            resp = await self._http.post(url, json=payload, headers={"Content-Type": "application/json"})
        if resp.status_code != 200:
            raise ValueError(f"Gemini API error: {resp.text}")
        data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            return ""
