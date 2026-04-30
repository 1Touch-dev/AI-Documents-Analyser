"""
Consulting Insights Skill — strict structured SWOT output.

Always returns a validated dict matching CONSULTING_OUTPUT_SCHEMA.
"""

from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)

CONSULTING_OUTPUT_SCHEMA = {
    "strengths": [],
    "weaknesses": [],
    "opportunities": [],
    "threats": [],
    "strategic_actions": [],
}

SYSTEM_PROMPT = """You are a senior business consultant AI.
Perform a SWOT analysis and strategic assessment. Return ONLY valid JSON matching this exact schema.
Do NOT include any explanation, markdown, or text outside the JSON object.

Schema:
{
  "strengths": ["<string>", ...],
  "weaknesses": ["<string>", ...],
  "opportunities": ["<string>", ...],
  "threats": ["<string>", ...],
  "strategic_actions": ["<actionable recommendation>", ...]
}

Rules:
- Each array must have at least 3 items.
- strategic_actions must be specific, actionable next steps.
- Return ONLY the JSON object. No markdown fences, no commentary.
"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"LLM returned non-JSON output: {text[:200]}")


def _merge_with_schema(data: dict) -> dict:
    import copy
    result = copy.deepcopy(CONSULTING_OUTPUT_SCHEMA)
    for field in ("strengths", "weaknesses", "opportunities", "threats", "strategic_actions"):
        if field in data and isinstance(data[field], list):
            result[field] = [str(x) for x in data[field]]
    return result


async def generate_consulting_insights(
    context: str,
    llm_router,
    model: str = "gpt-4o",
    api_keys: dict | None = None,
    provider: str = "openai",
) -> dict:
    """
    Generate SWOT-style consulting insights.
    Returns strict JSON conforming to CONSULTING_OUTPUT_SCHEMA.
    """
    from backend.llm_router import _is_bedrock_provider
    if _is_bedrock_provider(provider):
        from config.settings import settings
        resolved_model = model or settings.bedrock_default_model
    else:
        resolved_model = model or "gpt-4o"

    prompt = f"""Perform a comprehensive SWOT analysis and strategic assessment based on the following context.

CONTEXT:
{context[:6000]}

Return ONLY the JSON object matching the schema. No markdown, no explanation."""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    raw = await llm_router.generate(
        model_name=resolved_model,
        messages=messages,
        temperature=0.3,
        max_tokens=2500,
        api_keys=api_keys,
        provider=provider,
    )

    try:
        data = _extract_json(raw)
        result = _merge_with_schema(data)
    except Exception as exc:
        logger.warning("Consulting insights JSON parse failed (%s) — returning defaults.", exc)
        result = _merge_with_schema({})

    result["model_used"] = resolved_model
    result["skill"] = "consulting_insights"
    return result
