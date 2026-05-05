"""
Workflow Engine — orchestrates multi-step AI pipelines.

Each workflow is:
  Documents → Step 1 → Step 2 → … → Structured Output

Usage:
    result = await run_workflow("financial", input_data, llm_router, provider, model, api_keys)
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# Registry of available workflows (populated by imports below)
WORKFLOW_REGISTRY: dict[str, dict[str, Any]] = {}


def register_workflow(name: str, meta: dict[str, Any]):
    WORKFLOW_REGISTRY[name] = meta


async def run_workflow(
    workflow_name: str,
    input_data: dict,
    llm_router,
    provider: str = "openai",
    model: str = "auto",
    api_keys: dict | None = None,
) -> dict:
    """
    Execute a named workflow end-to-end.

    Returns a dict with:
      - workflow: name
      - steps: list of completed step names
      - result: the final structured output
      - duration_ms: total execution time
      - model_used: resolved model ID
      - provider: provider used
    """
    if workflow_name not in WORKFLOW_REGISTRY:
        raise ValueError(
            f"Unknown workflow '{workflow_name}'. "
            f"Available: {list(WORKFLOW_REGISTRY.keys())}"
        )

    meta = WORKFLOW_REGISTRY[workflow_name]
    handler = meta["handler"]

    logger.info("Running workflow '%s' with provider=%s model=%s", workflow_name, provider, model)
    t0 = time.perf_counter()

    result = await handler(
        input_data=input_data,
        llm_router=llm_router,
        provider=provider,
        model=model,
        api_keys=api_keys,
    )

    duration_ms = int((time.perf_counter() - t0) * 1000)
    result.setdefault("workflow", workflow_name)
    result.setdefault("provider", provider)
    result["duration_ms"] = duration_ms

    logger.info("Workflow '%s' completed in %dms", workflow_name, duration_ms)
    return result


def list_workflows() -> list[dict[str, Any]]:
    """Return metadata for all registered workflows."""
    return [
        {
            "name": name,
            "label": meta.get("label", name),
            "description": meta.get("description", ""),
            "steps": meta.get("steps", []),
            "output_schema": meta.get("output_schema", {}),
        }
        for name, meta in WORKFLOW_REGISTRY.items()
    ]


# ── Auto-register all workflows on import ─────────────────────────────────────
from backend.workflows import (
    financial_workflow,
    consulting_workflow,
    report_workflow,
    debt_workflow
)
