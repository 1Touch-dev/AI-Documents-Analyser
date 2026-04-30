"""
AWS Bedrock Service – multi-model generation via the Bedrock Converse API.

Supports all Bedrock-hosted model families:
  • Anthropic Claude (Opus 4.7, Sonnet 4.6, Haiku)
  • Amazon Nova (Micro, Lite, Pro)
  • Meta Llama 3 (via Bedrock)
  • Mistral / Mixtral (via Bedrock)
  • Cohere Command R+

All calls go through the unified `converse` API so switching models
requires only a modelId change — no per-provider SDK code.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)

# ── Dynamic Model Registry ────────────────────────────────────────────────────
# Keys are friendly names used in API requests; values are Bedrock modelIds.
# The "us." prefix enables cross-region inference profiles (recommended by AWS).

BEDROCK_MODELS: dict[str, str] = {
    # ── Anthropic Claude ──────────────────────────────────────────────────────
    "claude-opus-4.7":    "us.anthropic.claude-opus-4-7-20260416-v1:0",
    "claude-opus-4.6":    "us.anthropic.claude-opus-4-5-20251101-v1:0",
    "claude-sonnet-4.6":  "us.anthropic.claude-sonnet-4-5-20251203-v1:0",
    "claude-haiku":       "us.anthropic.claude-haiku-3-5-20241022-v1:0",
    # ── Amazon Nova ──────────────────────────────────────────────────────────
    "nova-micro":         "amazon.nova-micro-v1:0",
    "nova-lite":          "amazon.nova-lite-v1:0",
    "nova-pro":           "amazon.nova-pro-v1:0",
    # ── Meta Llama ───────────────────────────────────────────────────────────
    "llama3-70b":         "us.meta.llama3-70b-instruct-v1:0",
    "llama3-8b":          "us.meta.llama3-8b-instruct-v1:0",
    # ── Mistral ──────────────────────────────────────────────────────────────
    "mistral-large":      "mistral.mistral-large-2402-v1:0",
    "mixtral-8x7b":       "mistral.mixtral-8x7b-instruct-v0:1",
    # ── Cohere ───────────────────────────────────────────────────────────────
    "cohere-command-r+":  "cohere.command-r-plus-v1:0",
}

# Default model when none is specified
DEFAULT_BEDROCK_MODEL = "nova-lite"


class BedrockService:
    """
    Async wrapper around the AWS Bedrock Runtime converse API.

    The converse API provides a single, unified interface for all Bedrock
    models, regardless of provider — no per-provider request formatting needed.
    """

    def __init__(self) -> None:
        self.client = boto3.client(
            service_name="bedrock-runtime",
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def resolve_model_id(self, friendly_name: str) -> str:
        """Map a friendly model name to a Bedrock modelId. Falls back to nova-lite."""
        if friendly_name in BEDROCK_MODELS:
            return BEDROCK_MODELS[friendly_name]
        # Check if caller already passed a raw modelId
        if "." in friendly_name or ":" in friendly_name:
            return friendly_name
        logger.warning(
            "Unknown Bedrock model '%s'; defaulting to '%s'.",
            friendly_name,
            DEFAULT_BEDROCK_MODEL,
        )
        return BEDROCK_MODELS[DEFAULT_BEDROCK_MODEL]

    def generate_sync(
        self,
        prompt: str,
        model_id: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """
        Synchronous generation via the Bedrock converse API.
        Used internally; prefer `generate()` for async contexts.
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
            error_code = exc.response["Error"]["Code"]
            error_msg = exc.response["Error"]["Message"]
            logger.error("Bedrock ClientError [%s]: %s", error_code, error_msg)
            raise RuntimeError(f"Bedrock error ({error_code}): {error_msg}") from exc
        except NoCredentialsError as exc:
            raise RuntimeError(
                "AWS credentials not configured. Set AWS_ACCESS_KEY_ID and "
                "AWS_SECRET_ACCESS_KEY in your environment."
            ) from exc

    async def generate(
        self,
        prompt: str,
        model_name: str = DEFAULT_BEDROCK_MODEL,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """
        Async generation — runs boto3 (synchronous) in a thread pool so it
        doesn't block the FastAPI event loop.
        """
        model_id = self.resolve_model_id(model_name)
        logger.info("Bedrock generate: model_name=%s → model_id=%s", model_name, model_id)
        return await asyncio.to_thread(
            self.generate_sync,
            prompt,
            model_id,
            system_prompt,
            temperature,
            max_tokens,
        )

    async def generate_from_messages(
        self,
        messages: list[dict[str, str]],
        model_name: str = DEFAULT_BEDROCK_MODEL,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """
        Accept OpenAI-style messages list and convert to Bedrock converse format.
        System messages are extracted and passed via the `system` parameter.
        """
        system_parts: list[str] = []
        bedrock_messages: list[dict[str, Any]] = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_parts.append(content)
            else:
                bedrock_role = "assistant" if role == "assistant" else "user"
                bedrock_messages.append(
                    {"role": bedrock_role, "content": [{"text": content}]}
                )

        system_prompt = "\n\n".join(system_parts) if system_parts else None
        # Flatten to a single prompt for the generate call
        combined_prompt = "\n\n".join(
            m["content"][0]["text"] for m in bedrock_messages if m["role"] == "user"
        )

        return await self.generate(
            prompt=combined_prompt,
            model_name=model_name,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @staticmethod
    def list_models() -> list[dict[str, str]]:
        """Return all registered Bedrock models as a list of {name, model_id} dicts."""
        return [
            {"name": k, "model_id": v, "provider": _infer_provider(k)}
            for k, v in BEDROCK_MODELS.items()
        ]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _infer_provider(friendly_name: str) -> str:
    if friendly_name.startswith("claude"):
        return "Anthropic"
    if friendly_name.startswith("nova"):
        return "Amazon"
    if friendly_name.startswith("llama"):
        return "Meta"
    if friendly_name.startswith("mistral") or friendly_name.startswith("mixtral"):
        return "Mistral"
    if friendly_name.startswith("cohere"):
        return "Cohere"
    return "AWS"


# ── Module-level singleton ────────────────────────────────────────────────────
_bedrock_service: BedrockService | None = None


def get_bedrock_service() -> BedrockService:
    global _bedrock_service
    if _bedrock_service is None:
        _bedrock_service = BedrockService()
    return _bedrock_service
