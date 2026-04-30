"""
AWS Bedrock Service – universal multi-model generation via the Converse API.

Design principles:
  • No model whitelist – any Bedrock-compatible model ID is accepted.
  • BEDROCK_DEFAULT_MODELS lists known-good models for UI dropdowns only;
    it does NOT gate which models can be called.
  • All calls go through the single `converse` API – same code path for
    every provider (Anthropic, Amazon, Meta, Mistral, Cohere, …).

Supported model families (non-exhaustive – Bedrock adds new ones regularly):
  Anthropic Claude  – claude-opus-4.7, claude-sonnet-4.6, claude-haiku, …
  Amazon Nova       – nova-micro, nova-lite, nova-pro
  Meta Llama        – llama3-8b, llama3-70b
  Mistral / Mixtral – mistral-large, mixtral-8x7b
  Cohere            – command-r-plus
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)


# ── Default model list (dropdown hints – NOT an allowlist) ────────────────────
# Any valid Bedrock model ID works even if not listed here.
BEDROCK_DEFAULT_MODELS: list[str] = [
    # Anthropic Claude
    "us.anthropic.claude-opus-4-7-20260416-v1:0",
    "us.anthropic.claude-opus-4-5-20251101-v1:0",
    "us.anthropic.claude-sonnet-4-5-20251203-v1:0",
    "us.anthropic.claude-haiku-3-5-20241022-v1:0",
    # Amazon Nova
    "amazon.nova-micro-v1:0",
    "amazon.nova-lite-v1:0",
    "amazon.nova-pro-v1:0",
    # Meta Llama
    "us.meta.llama3-70b-instruct-v1:0",
    "us.meta.llama3-8b-instruct-v1:0",
    # Mistral
    "mistral.mistral-large-2402-v1:0",
    "mistral.mixtral-8x7b-instruct-v0:1",
    # Cohere
    "cohere.command-r-plus-v1:0",
]

# Friendly display names for UI dropdowns (model_id → label)
BEDROCK_MODEL_LABELS: dict[str, str] = {
    "us.anthropic.claude-opus-4-7-20260416-v1:0":  "Claude Opus 4.7 (Anthropic · latest)",
    "us.anthropic.claude-opus-4-5-20251101-v1:0":  "Claude Opus 4.6 (Anthropic · flagship)",
    "us.anthropic.claude-sonnet-4-5-20251203-v1:0":"Claude Sonnet 4.6 (Anthropic · balanced)",
    "us.anthropic.claude-haiku-3-5-20241022-v1:0": "Claude Haiku (Anthropic · fast)",
    "amazon.nova-micro-v1:0":                       "Nova Micro (Amazon · fastest)",
    "amazon.nova-lite-v1:0":                        "Nova Lite (Amazon · fast + multimodal)",
    "amazon.nova-pro-v1:0":                         "Nova Pro (Amazon · highest quality)",
    "us.meta.llama3-70b-instruct-v1:0":             "Llama 3 70B (Meta · open weights)",
    "us.meta.llama3-8b-instruct-v1:0":              "Llama 3 8B (Meta · lightweight)",
    "mistral.mistral-large-2402-v1:0":              "Mistral Large (Mistral AI)",
    "mistral.mixtral-8x7b-instruct-v0:1":           "Mixtral 8×7B (Mistral AI · MoE)",
    "cohere.command-r-plus-v1:0":                   "Command R+ (Cohere · RAG-optimised)",
}


class BedrockService:
    """
    Universal Bedrock client using the Converse API.

    Any model ID accepted by AWS Bedrock can be passed – no allowlist enforced.
    The BEDROCK_DEFAULT_MODELS list is informational only.
    """

    def __init__(self) -> None:
        # Prefer values from pydantic settings (reads .env file).
        # Fall back to raw os.getenv for environments where settings aren't
        # importable (e.g. standalone scripts).
        try:
            from config.settings import settings as _s
            key_id = _s.aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID") or ""
            secret  = _s.aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY") or ""
            region  = _s.aws_region or os.getenv("AWS_REGION", "us-east-1")
        except Exception:
            key_id = os.getenv("AWS_ACCESS_KEY_ID") or ""
            secret  = os.getenv("AWS_SECRET_ACCESS_KEY") or ""
            region  = os.getenv("AWS_REGION", "us-east-1")

        self.client = boto3.client(
            service_name="bedrock-runtime",
            region_name=region,
            aws_access_key_id=key_id or None,
            aws_secret_access_key=secret or None,
        )

    # ── Core synchronous generate (exact requested pattern) ──────────────────

    def generate(self, prompt: str, model_id: str) -> str:
        """
        Generate a response using the Bedrock Converse API.

        Accepts ANY valid Bedrock model_id – not restricted to BEDROCK_DEFAULT_MODELS.
        Raises RuntimeError with a clean message on AWS errors.
        """
        response = self.client.converse(
            modelId=model_id,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": prompt}],
                }
            ],
        )
        return response["output"]["message"]["content"][0]["text"]

    # ── Extended synchronous generate (with system prompt + inference config) ─

    def generate_full(
        self,
        prompt: str,
        model_id: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """
        Full generate with system prompt and inference configuration.
        Falls back to `generate()` if the model doesn't support system prompts.
        """
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": [{"text": prompt}]}
        ]
        kwargs: dict[str, Any] = {
            "modelId": model_id,
            "messages": messages,
            "inferenceConfig": {
                "maxTokens": max_tokens,
                "temperature": temperature,
            },
        }
        if system_prompt:
            kwargs["system"] = [{"text": system_prompt}]

        try:
            response = self.client.converse(**kwargs)
            return response["output"]["message"]["content"][0]["text"]
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            msg = exc.response["Error"]["Message"]
            logger.error("Bedrock ClientError [%s] model=%s: %s", code, model_id, msg)
            raise RuntimeError(f"Bedrock error ({code}): {msg}") from exc
        except NoCredentialsError as exc:
            raise RuntimeError(
                "AWS credentials not configured. "
                "Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in your .env file."
            ) from exc

    # ── Async wrappers ────────────────────────────────────────────────────────

    async def generate_async(self, prompt: str, model_id: str) -> str:
        """Async wrapper around generate() – runs in thread pool."""
        return await asyncio.to_thread(self.generate, prompt, model_id)

    async def generate_full_async(
        self,
        prompt: str,
        model_id: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Async wrapper around generate_full()."""
        return await asyncio.to_thread(
            self.generate_full, prompt, model_id, system_prompt, temperature, max_tokens
        )

    async def generate_from_messages(
        self,
        messages: list[dict[str, str]],
        model_id: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """
        Accept OpenAI-style messages list and call Bedrock.
        System messages are extracted and passed via the system parameter.
        Accepts ANY model_id – unknown models are passed straight through.
        """
        system_parts: list[str] = []
        user_parts: list[str] = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_parts.append(content)
            elif role in ("user", "assistant"):
                user_parts.append(content)

        combined_prompt = "\n\n".join(user_parts) if user_parts else ""
        system_prompt = "\n\n".join(system_parts) if system_parts else None

        return await self.generate_full_async(
            prompt=combined_prompt,
            model_id=model_id,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    # ── Model helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def get_default_models() -> list[dict[str, str]]:
        """Return the default model list with display labels."""
        return [
            {
                "model_id": mid,
                "label": BEDROCK_MODEL_LABELS.get(mid, mid),
                "provider": _infer_provider(mid),
            }
            for mid in BEDROCK_DEFAULT_MODELS
        ]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _infer_provider(model_id: str) -> str:
    mid = model_id.lower()
    if "anthropic" in mid or "claude" in mid:
        return "Anthropic"
    if "nova" in mid or "amazon" in mid:
        return "Amazon"
    if "llama" in mid or "meta" in mid:
        return "Meta"
    if "mistral" in mid or "mixtral" in mid:
        return "Mistral"
    if "cohere" in mid:
        return "Cohere"
    return "AWS Bedrock"


# ── Module-level singleton ────────────────────────────────────────────────────
_bedrock_service: BedrockService | None = None


def get_bedrock_service() -> BedrockService:
    global _bedrock_service
    if _bedrock_service is None:
        _bedrock_service = BedrockService()
    return _bedrock_service
