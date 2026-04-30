"""
Report Generation Skill — strict structured output.

Always returns a validated dict matching REPORT_OUTPUT_SCHEMA.
"""

from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)

REPORT_OUTPUT_SCHEMA = {
    "title": "",
    "executive_summary": "",
    "key_metrics": {},
    "analysis": [],
    "recommendations": [],
}

SYSTEM_PROMPT = """You are a business report generation AI.
Generate a structured business report and return ONLY valid JSON matching this exact schema.
Do NOT include any explanation, markdown, or text outside the JSON object.

Schema:
{
  "title": "<report title string>",
  "executive_summary": "<2-4 sentence summary string>",
  "key_metrics": {"<metric_name>": "<value>", ...},
  "analysis": ["<finding string>", ...],
  "recommendations": ["<action string>", ...]
}

Rules:
- title must be a descriptive string.
- executive_summary must be 2-4 sentences.
- key_metrics must have at least 3 entries.
- analysis must have at least 3 items.
- recommendations must have at least 3 items.
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
    result = copy.deepcopy(REPORT_OUTPUT_SCHEMA)
    result["title"] = str(data.get("title", "Business Report"))
    result["executive_summary"] = str(data.get("executive_summary", ""))
    if "key_metrics" in data and isinstance(data["key_metrics"], dict):
        result["key_metrics"] = {str(k): str(v) for k, v in data["key_metrics"].items()}
    for field in ("analysis", "recommendations"):
        if field in data and isinstance(data[field], list):
            result[field] = [str(x) for x in data[field]]
    return result


async def generate_report(
    context: str,
    llm_router,
    model: str = "gpt-4o",
    api_keys: dict | None = None,
    provider: str = "openai",
) -> dict:
    """
    Generate a structured business report.
    Returns strict JSON conforming to REPORT_OUTPUT_SCHEMA.
    """
    from backend.llm_router import _is_bedrock_provider
    if _is_bedrock_provider(provider):
        from config.settings import settings
        resolved_model = model or settings.bedrock_default_model
    else:
        resolved_model = model or "gpt-4o"

    prompt = f"""Generate a comprehensive business report based on the following context.

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
        max_tokens=3000,
        api_keys=api_keys,
        provider=provider,
    )

    try:
        data = _extract_json(raw)
        result = _merge_with_schema(data)
    except Exception as exc:
        logger.warning("Report generation JSON parse failed (%s) — returning defaults.", exc)
        result = _merge_with_schema({})

    result["model_used"] = resolved_model
    result["skill"] = "report_generation"
    return result
