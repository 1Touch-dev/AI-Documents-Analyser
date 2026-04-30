"""
Financial Analysis Skill — strict structured output.

Always returns a validated dict matching FINANCIAL_OUTPUT_SCHEMA.
Never returns free text — the LLM is instructed to produce pure JSON.
"""

from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)

FINANCIAL_OUTPUT_SCHEMA = {
    "revenue": {
        "fnb": 0,
        "sponsorship": 0,
        "tickets": 0,
        "retail": 0,
        "player_sales": 0,
    },
    "expenses": {
        "player_salary": 0,
        "coach_salary": 0,
        "travel": 0,
        "stadium": 0,
        "retail": 0,
        "fnb": 0,
        "back_office": 0,
        "misc": 0,
    },
    "insights": [],
    "risks": [],
    "opportunities": [],
}

SYSTEM_PROMPT = """You are a financial analysis AI.
Extract financial data from the document and return ONLY valid JSON matching this exact schema.
Do NOT include any explanation, markdown, or text outside the JSON object.

Schema:
{
  "revenue": {"fnb": <number>, "sponsorship": <number>, "tickets": <number>, "retail": <number>, "player_sales": <number>},
  "expenses": {"player_salary": <number>, "coach_salary": <number>, "travel": <number>, "stadium": <number>, "retail": <number>, "fnb": <number>, "back_office": <number>, "misc": <number>},
  "insights": ["<string>", ...],
  "risks": ["<string>", ...],
  "opportunities": ["<string>", ...]
}

Rules:
- All monetary values must be numbers (not strings). Use 0 if not mentioned.
- insights, risks, opportunities must each have at least 2 items.
- Return ONLY the JSON object. No markdown fences, no commentary.
"""


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM output, stripping any markdown fences."""
    text = text.strip()
    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find a JSON object anywhere in the text
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"LLM returned non-JSON output: {text[:200]}")


def _merge_with_schema(data: dict) -> dict:
    """Merge LLM output with default schema, ensuring all keys exist."""
    import copy
    result = copy.deepcopy(FINANCIAL_OUTPUT_SCHEMA)
    if "revenue" in data and isinstance(data["revenue"], dict):
        result["revenue"].update({k: v for k, v in data["revenue"].items() if isinstance(v, (int, float))})
    if "expenses" in data and isinstance(data["expenses"], dict):
        result["expenses"].update({k: v for k, v in data["expenses"].items() if isinstance(v, (int, float))})
    for field in ("insights", "risks", "opportunities"):
        if field in data and isinstance(data[field], list):
            result[field] = [str(x) for x in data[field]]
    return result


async def analyze_financials(
    document_text: str,
    llm_router,
    model: str = "gpt-4o",
    api_keys: dict | None = None,
    provider: str = "openai",
) -> dict:
    """
    Run structured financial analysis against document text.
    Returns strict JSON conforming to FINANCIAL_OUTPUT_SCHEMA.
    """
    from backend.llm_router import _is_bedrock_provider
    if _is_bedrock_provider(provider):
        from config.settings import settings
        resolved_model = model or settings.bedrock_default_model
    else:
        resolved_model = model or "gpt-4o"

    prompt = f"""Analyse the following document and extract all financial data.

DOCUMENT:
{document_text[:6000]}

Return ONLY the JSON object matching the schema. No markdown, no explanation."""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    raw = await llm_router.generate(
        model_name=resolved_model,
        messages=messages,
        temperature=0.1,
        max_tokens=2048,
        api_keys=api_keys,
        provider=provider,
    )

    try:
        data = _extract_json(raw)
        result = _merge_with_schema(data)
    except Exception as exc:
        logger.warning("Financial analysis JSON parse failed (%s) — returning defaults.", exc)
        result = _merge_with_schema({})

    result["model_used"] = resolved_model
    result["skill"] = "financial_analysis"
    return result
