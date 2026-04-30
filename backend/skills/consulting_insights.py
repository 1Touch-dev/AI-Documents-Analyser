"""
Consulting Insights Skill – applies a McKinsey/BCG-style strategic framework
to document context and returns structured consulting output via GPT.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a management consultant with expertise in business strategy. "
    "Analyse the provided context and deliver structured, actionable consulting insights. "
    "Return only valid JSON — no markdown fences, no commentary."
)


def _build_prompt(context: str) -> str:
    schema = {
        "strengths": ["Competitive advantage or positive factor"],
        "weaknesses": ["Internal gap or limitation"],
        "opportunities": ["Market or strategic opportunity to pursue"],
        "risks": ["Threat or downside risk to monitor"],
        "strategic_priorities": [
            {
                "priority": "Priority title",
                "rationale": "Why this matters",
                "suggested_actions": ["Action step 1"],
            }
        ],
        "overall_assessment": "One-paragraph strategic assessment",
    }
    return (
        f"Provide consulting-style insights as JSON strictly matching this schema:\n\n"
        f"{json.dumps(schema, indent=2)}\n\n"
        f"Context:\n{context[:6000]}"
    )


async def generate_consulting_insights(
    context: str,
    llm_router: Any,
    model: str = "auto",
    api_keys: dict[str, str | None] | None = None,
    provider: str = "openai",
) -> dict[str, Any]:
    """
    Provide consulting-style strategic insights from document context.

    Returns a dict with keys:
      - strengths              (list of strings)
      - weaknesses             (list of strings)
      - opportunities          (list of strings)
      - risks                  (list of strings)
      - strategic_priorities   (list of {priority, rationale, suggested_actions})
      - overall_assessment     (string)
    """
    if not context or not context.strip():
        return _empty_result("No context provided.")

    resolved_model = (
        model if provider == "bedrock"
        else llm_router.resolve_model(model, "analyze strategy recommend comprehensive", api_keys)
    )
    prompt = _build_prompt(context)

    try:
        raw = await llm_router.generate(
            model_name=resolved_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=2048,
            api_keys=api_keys,
            provider=provider,
        )
        result = _parse_json(raw)
        result["model_used"] = resolved_model
        result["skill"] = "consulting_insights"
        return result
    except Exception as exc:
        logger.warning("consulting_insights skill failed: %s", exc)
        fallback = _empty_result(f"Consulting analysis failed: {exc}")
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
        "skill": "consulting_insights",
        "strengths": [],
        "weaknesses": [reason],
        "opportunities": [],
        "risks": [reason],
        "strategic_priorities": [],
        "overall_assessment": reason,
        "model_used": "n/a",
    }
