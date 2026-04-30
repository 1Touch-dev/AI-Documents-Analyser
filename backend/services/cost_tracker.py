"""
LLM Cost Tracker
================
Logs per-request token usage and estimated cost to the llm_usage DB table.

Cost reference (approximate, as of 2026):
  OpenAI:
    gpt-4o:        $2.50/1M input, $10.00/1M output
    gpt-4.1:       $2.00/1M input,  $8.00/1M output
    gpt-4.1-mini:  $0.40/1M input,  $1.60/1M output
    gpt-3.5-turbo: $0.50/1M input,  $1.50/1M output

  AWS Bedrock (on-demand):
    claude-opus-4.7:  $15.00/1M input, $75.00/1M output
    claude-sonnet-4.x: $3.00/1M input, $15.00/1M output
    claude-haiku:      $0.25/1M input,  $1.25/1M output
    nova-micro:        $0.035/1M input, $0.14/1M output
    nova-lite:         $0.06/1M input,  $0.24/1M output
    nova-pro:          $0.80/1M input,  $3.20/1M output
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# ── Pricing tables (USD per 1 million tokens) ─────────────────────────────────

_OPENAI_PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o":         (2.50,  10.00),
    "gpt-4.1":        (2.00,   8.00),
    "gpt-4.1-mini":   (0.40,   1.60),
    "gpt-4o-mini":    (0.15,   0.60),
    "gpt-4-turbo":    (10.00, 30.00),
    "gpt-3.5-turbo":  (0.50,   1.50),
}

_BEDROCK_PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-4-7":   (15.00, 75.00),
    "claude-opus-4-5":   (15.00, 75.00),
    "claude-sonnet-4-5": (3.00,  15.00),
    "claude-haiku-3-5":  (0.80,   4.00),
    "claude-haiku":      (0.25,   1.25),
    "nova-pro":          (0.80,   3.20),
    "nova-lite":         (0.06,   0.24),
    "nova-micro":        (0.035,  0.14),
    "llama":             (0.40,   0.60),
    "mistral":           (0.45,   0.70),
    "cohere":            (0.50,   1.50),
}

_DEFAULT_PRICING = (1.00, 4.00)  # fallback per 1M tokens


def _resolve_pricing(provider: str, model: str) -> tuple[float, float]:
    model_lower = model.lower()
    if provider == "openai":
        for key, price in _OPENAI_PRICING.items():
            if key in model_lower:
                return price
    elif provider == "bedrock":
        for key, price in _BEDROCK_PRICING.items():
            if key in model_lower:
                return price
    return _DEFAULT_PRICING


def estimate_cost(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> str:
    """Return estimated cost as a formatted string like '0.0023'."""
    input_rate, output_rate = _resolve_pricing(provider, model)
    cost = (prompt_tokens * input_rate + completion_tokens * output_rate) / 1_000_000
    return f"{cost:.6f}"


def estimate_tokens_from_text(text: str) -> int:
    """Rough token estimate: ~4 chars per token (GPT-style BPE)."""
    return max(1, len(text) // 4)


# ── DB logging ────────────────────────────────────────────────────────────────

def log_usage(
    db,
    provider: str,
    model: str,
    action: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    user=None,
) -> None:
    """
    Write a usage record to llm_usage table.
    Fire-and-forget — errors are logged but never raised.
    """
    try:
        from db.models import LLMUsage
        total = prompt_tokens + completion_tokens
        cost_str = estimate_cost(provider, model, prompt_tokens, completion_tokens)
        record = LLMUsage(
            user_id=getattr(user, "id", None),
            username=getattr(user, "username", None),
            provider=provider,
            model=model,
            action=action,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total,
            cost_usd=cost_str,
        )
        db.add(record)
        db.commit()
        logger.debug(
            "LLM usage logged: %s/%s %dtok $%s (user=%s)",
            provider, model, total, cost_str, getattr(user, "username", "anon"),
        )
    except Exception as exc:
        logger.warning("Cost tracking write failed: %s", exc)


async def log_usage_async(
    db,
    provider: str,
    model: str,
    action: str,
    prompt_text: str = "",
    completion_text: str = "",
    user=None,
) -> None:
    """Async wrapper that estimates tokens from raw text then calls log_usage."""
    prompt_tokens = estimate_tokens_from_text(prompt_text)
    completion_tokens = estimate_tokens_from_text(completion_text)
    log_usage(
        db=db,
        provider=provider,
        model=model,
        action=action,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        user=user,
    )


def get_usage_summary(db, user=None, days: int = 30) -> dict:
    """Return aggregated usage stats for a user (or all users if admin)."""
    try:
        from db.models import LLMUsage
        from datetime import timedelta
        from sqlalchemy import func

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        query = db.query(LLMUsage).filter(LLMUsage.timestamp >= cutoff)
        if user and getattr(user, "role", "user") != "admin":
            query = query.filter(LLMUsage.username == user.username)

        records = query.all()
        total_tokens = sum(r.total_tokens or 0 for r in records)
        total_cost = sum(float(r.cost_usd or 0) for r in records)

        by_model: dict[str, dict] = {}
        for r in records:
            key = f"{r.provider}/{r.model}"
            entry = by_model.setdefault(key, {"requests": 0, "tokens": 0, "cost": 0.0})
            entry["requests"] += 1
            entry["tokens"] += r.total_tokens or 0
            entry["cost"] += float(r.cost_usd or 0)

        return {
            "period_days": days,
            "total_requests": len(records),
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4),
            "cost_type": "estimated",  # token counts are character-length approximations
            "by_model": {k: {**v, "cost": round(v["cost"], 4)} for k, v in by_model.items()},
        }
    except Exception as exc:
        logger.warning("Usage summary failed: %s", exc)
        return {"error": str(exc)}
