"""
Retry + Timeout Utility
=======================
Wraps async callables with configurable retry logic and per-call timeout.

Usage:
    result = await with_retry(my_async_fn, arg1, arg2, max_retries=2, timeout_s=30.0)
"""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

_FALLBACK_RESPONSE = {
    "error": "AI model temporarily unavailable. Please retry in a moment.",
    "fallback": True,
}


async def with_retry(
    fn,
    *args,
    max_retries: int = 2,
    timeout_s: float = 60.0,
    backoff_s: float = 2.0,
    fallback: dict | None = None,
    **kwargs,
):
    """
    Call async `fn(*args, **kwargs)` with up to `max_retries` retries.

    Each attempt is wrapped with asyncio.wait_for(timeout_s).
    On permanent failure, returns `fallback` dict (or raises if fallback=None).
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return await asyncio.wait_for(fn(*args, **kwargs), timeout=timeout_s)
        except asyncio.TimeoutError as exc:
            last_exc = exc
            logger.warning(
                "Attempt %d/%d timed out after %.1fs for %s",
                attempt + 1, max_retries + 1, timeout_s, getattr(fn, "__name__", "?"),
            )
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "Attempt %d/%d failed for %s: %s",
                attempt + 1, max_retries + 1, getattr(fn, "__name__", "?"), exc,
            )

        if attempt < max_retries:
            wait = backoff_s * (2 ** attempt)  # exponential backoff: 2s, 4s
            logger.info("Retrying in %.1fs…", wait)
            await asyncio.sleep(wait)

    if fallback is not None:
        logger.error("All %d attempts failed — returning fallback response", max_retries + 1)
        return fallback

    raise last_exc or RuntimeError("All retry attempts exhausted")


def make_workflow_fallback(workflow_name: str) -> dict:
    return {
        "workflow": workflow_name,
        "steps": [],
        "result": {},
        "error": "Workflow failed after retries. Please check model availability.",
        "fallback": True,
        "duration_ms": 0,
    }
