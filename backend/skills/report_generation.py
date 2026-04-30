"""
Report Generation Skill – produces a structured business report from
document context using GPT.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a senior business analyst. Generate a structured, professional business "
    "report from the provided context. Return only valid JSON — no markdown fences, "
    "no commentary."
)


def _build_prompt(context: str) -> str:
    schema = {
        "title": "Report title",
        "executive_summary": "1-2 paragraph executive summary",
        "key_metrics": [{"metric": "Name", "value": "Value", "note": "Optional note"}],
        "findings": ["Key finding 1", "Key finding 2"],
        "recommendations": ["Action item 1", "Action item 2"],
        "conclusion": "Closing paragraph summarising next steps",
    }
    return (
        f"Generate a structured business report as JSON strictly matching this schema:\n\n"
        f"{json.dumps(schema, indent=2)}\n\n"
        f"Context:\n{context[:6000]}"
    )


async def generate_report(
    context: str,
    llm_router: Any,
    model: str = "auto",
    api_keys: dict[str, str | None] | None = None,
    provider: str = "openai",
) -> dict[str, Any]:
    """
    Generate a structured business report from document context.

    Returns a dict with keys:
      - title
      - executive_summary
      - key_metrics       (list of {metric, value, note})
      - findings          (list of strings)
      - recommendations   (list of strings)
      - conclusion
    """
    if not context or not context.strip():
        return _empty_result("No context provided.")

    from backend.llm_router import _is_bedrock_provider
    from config.settings import settings as _settings
    resolved_model = (
        (model or "").strip() or _settings.bedrock_default_model
        if _is_bedrock_provider(provider)
        else llm_router.resolve_model(model, "generate report comprehensive", api_keys)
    )
    prompt = _build_prompt(context)

    try:
        raw = await llm_router.generate(
            model_name=resolved_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=2048,
            api_keys=api_keys,
            provider=provider,
        )
        result = _parse_json(raw)
        result["model_used"] = resolved_model
        result["skill"] = "report_generation"
        return result
    except Exception as exc:
        logger.warning("report_generation skill failed: %s", exc)
        fallback = _empty_result(f"Report generation failed: {exc}")
        fallback["model_used"] = resolved_model
        return fallback


def _parse_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        lines = [ln for ln in text.splitlines() if not ln.strip().startswith("```")]
        text = "\n".join(lines).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object in model output.")
    return json.loads(text[start: end + 1])


def _empty_result(reason: str) -> dict[str, Any]:
    return {
        "skill": "report_generation",
        "title": "Report Unavailable",
        "executive_summary": reason,
        "key_metrics": [],
        "findings": [reason],
        "recommendations": [],
        "conclusion": reason,
        "model_used": "n/a",
    }
