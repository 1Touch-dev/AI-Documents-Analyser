"""
LLM Router – routes queries to the appropriate language model.

Supports:
  • Ollama (Llama 3, Mistral, Mixtral, Gemma)
  • OpenAI (GPT-4 / GPT-3.5)
  • Anthropic (Claude)

Includes an 'auto' routing mode that sends simple queries to local
models and complex reasoning to more powerful external models.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, AsyncIterator

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# Supported models
# ──────────────────────────────────────────────────────────
class ModelProvider(str, Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


# Model → provider mapping
MODEL_REGISTRY: dict[str, dict[str, Any]] = {
    # ── Ollama (local) ────────────────────────────────
    "llama3.2": {"provider": ModelProvider.OLLAMA, "model_id": "llama3.2"},
    "tinyllama": {"provider": ModelProvider.OLLAMA, "model_id": "tinyllama"},
    "llama3": {"provider": ModelProvider.OLLAMA, "model_id": "llama3"},
    "llama3.1": {"provider": ModelProvider.OLLAMA, "model_id": "llama3.1"},
    "mistral": {"provider": ModelProvider.OLLAMA, "model_id": "mistral"},
    "mixtral": {"provider": ModelProvider.OLLAMA, "model_id": "mixtral"},
    "gemma": {"provider": ModelProvider.OLLAMA, "model_id": "gemma"},
    "gemma2": {"provider": ModelProvider.OLLAMA, "model_id": "gemma2"},
    # ── OpenAI ────────────────────────────────────────
    "gpt-5.4": {"provider": ModelProvider.OPENAI, "model_id": "gpt-5.4"},
    "o3-mini": {"provider": ModelProvider.OPENAI, "model_id": "o3-mini"},
    "gpt-4o": {"provider": ModelProvider.OPENAI, "model_id": "gpt-4o"},
    # ── Anthropic ─────────────────────────────────────
    "claude-4.6-opus": {"provider": ModelProvider.ANTHROPIC, "model_id": "claude-4.6-opus-20260205"},
    "claude-4.6-sonnet": {"provider": ModelProvider.ANTHROPIC, "model_id": "claude-4.6-sonnet-20260217"},
    "claude-3.5-sonnet": {"provider": ModelProvider.ANTHROPIC, "model_id": "claude-3-5-sonnet-20241022"},
    # ── Gemini ────────────────────────────────────────
    "gemini-3.1-pro": {"provider": ModelProvider.GEMINI, "model_id": "gemini-3.1-pro-preview"},
    "gemini-3-flash": {"provider": ModelProvider.GEMINI, "model_id": "gemini-3-flash"},
    "gemini-3.1-flash": {"provider": ModelProvider.GEMINI, "model_id": "gemini-3.1-flash-lite-preview"},
}

# ── Auto-routing heuristic ────────────────────────────────
_COMPLEX_KEYWORDS = {
    "analyze", "compare", "evaluate", "synthesize", "strategy",
    "recommend", "design", "architecture", "complex", "detailed",
    "comprehensive", "multi-step", "reasoning", "explain why",
}


def _is_complex_query(query: str) -> bool:
    """Simple heuristic: complex if query is long or contains keywords."""
    q = query.lower()
    if len(query) > 300:
        return True
    return any(kw in q for kw in _COMPLEX_KEYWORDS)


# ──────────────────────────────────────────────────────────
# Router
# ──────────────────────────────────────────────────────────
class LLMRouter:
    """Route queries to the correct LLM backend."""

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(timeout=120.0)

    async def close(self) -> None:
        await self._http.aclose()

    # ── Public API ───────────────────────────────────────
    def list_models(self) -> list[str]:
        """Return all registered model names."""
        return sorted(MODEL_REGISTRY.keys())

    def resolve_model(self, model_name: str, query: str = "", api_keys: dict[str, str | None] | None = None) -> str:
        """Resolve 'auto' or validate a model name."""
        if model_name == "auto":
            if _is_complex_query(query):
                keys = api_keys or {}
                if keys.get("openai_api_key") or settings.openai_api_key:
                    return "gpt-5.4"
                if keys.get("gemini_api_key"):
                    return "gemini-3.1-pro"
                if keys.get("anthropic_api_key") or settings.anthropic_api_key:
                    return "claude-4.6-sonnet"
            return "llama3.2"
        if model_name not in MODEL_REGISTRY:
            raise ValueError(
                f"Unknown model '{model_name}'. Available: {self.list_models()}"
            )
        return model_name

    async def generate(
        self,
        model_name: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        api_keys: dict[str, str | None] | None = None,
    ) -> str:
        """
        Send a chat-completion request to the appropriate provider.

        Parameters
        ----------
        model_name : str
            Registered name (e.g. ``"llama3"``, ``"gpt-4o"``).
        messages : list
            OpenAI-style ``[{role, content}]`` list.
        """
        info = MODEL_REGISTRY.get(model_name)
        if not info:
            raise ValueError(f"Unknown model: {model_name}")

        provider = info["provider"]
        model_id = info["model_id"]

        if provider == ModelProvider.OLLAMA:
            return await self._call_ollama(model_id, messages, temperature, max_tokens)
        elif provider == ModelProvider.OPENAI:
            return await self._call_openai(model_id, messages, temperature, max_tokens, api_keys)
        elif provider == ModelProvider.ANTHROPIC:
            return await self._call_anthropic(model_id, messages, temperature, max_tokens, api_keys)
        elif provider == ModelProvider.GEMINI:
            return await self._call_gemini(model_id, messages, temperature, max_tokens, api_keys)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    # ── Ollama ───────────────────────────────────────────
    async def _call_ollama(
        self, model_id: str, messages: list[dict], temperature: float, max_tokens: int
    ) -> str:
        url = f"{settings.ollama_base_url}/api/chat"
        payload = {
            "model": model_id,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": max(0.1, temperature - 0.2),  # Lower temp for small models to stay focused
                "num_predict": max_tokens,
                "repeat_penalty": 1.2,  # Prevent infinite loops in tiny models
            },
        }
        resp = await self._http.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")

    # ── OpenAI ───────────────────────────────────────────
    async def _call_openai(
        self, model_id: str, messages: list[dict], temperature: float, max_tokens: int, api_keys: dict | None
    ) -> str:
        from openai import AsyncOpenAI

        keys = api_keys or {}
        api_key = keys.get("openai_api_key") or settings.openai_api_key
        if not api_key:
            raise ValueError("OpenAI API key missing. Please provide it in the UI or .env settings.")

        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
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
            raise ValueError("Anthropic API key missing. Please provide it in the UI or .env settings.")

        client = AsyncAnthropic(api_key=api_key)

        # Convert OpenAI-style messages → Anthropic format
        system_msg = ""
        anthropic_messages = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                anthropic_messages.append({"role": m["role"], "content": m["content"]})

        response = await client.messages.create(
            model=model_id,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_msg,
            messages=anthropic_messages,
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
        
        gemini_messages = []
        system_instructions = []
        
        for m in messages:
            if m["role"] == "system":
                system_instructions.append(m["content"])
            else:
                role = "user" if m["role"] == "user" else "model"
                gemini_messages.append({
                    "role": role,
                    "parts": [{"text": m["content"]}]
                })
                
        payload = {
            "contents": gemini_messages,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }
        
        if system_instructions:
            payload["systemInstruction"] = {
                "parts": [{"text": "\n".join(system_instructions)}]
            }
            
        resp = await self._http.post(url, json=payload, headers={"Content-Type": "application/json"})
        
        # Fallback to v1 if v1beta fails with 404
        if resp.status_code == 404:
            url_v1 = f"https://generativelanguage.googleapis.com/v1/models/{model_id}:generateContent?key={api_key}"
            resp = await self._http.post(url_v1, json=payload, headers={"Content-Type": "application/json"})

        if resp.status_code != 200:
            raise ValueError(f"Gemini API error: {resp.text}")
            
        data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            return ""
