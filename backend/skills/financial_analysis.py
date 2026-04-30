"""
Financial Analysis Skill – extracts structured revenue, expense, and insight
data from document text using GPT.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a senior financial analyst. Extract and structure financial information "
    "from the provided document text. Return only valid JSON — no markdown fences, "
    "no commentary."
)

OUTPUT_SCHEMA = {
    "revenue_breakdown": {
        "description": "Revenue items with label and amount (numbers only, 0 if unknown)",
        "example": [{"label": "Product Sales", "amount": 0}],
    },
    "expense_breakdown": {
        "description": "Expense items with label and amount",
        "example": [{"label": "Operating Costs", "amount": 0}],
    },
    "key_insights": {
        "description": "3-5 bullet-point insights about financial health",
        "example": ["Revenue exceeds expenses by 20%"],
    },
    "risk_flags": {
        "description": "Any financial risks or anomalies detected",
        "example": ["High debt-to-equity ratio"],
    },
    "summary": {
        "description": "One-paragraph financial summary",
        "example": "The organisation shows stable revenue with controlled expenditure.",
    },
}


def _build_prompt(document_text: str) -> str:
    schema_str = json.dumps(OUTPUT_SCHEMA, indent=2)
    return (
        f"Analyse the following document and return a JSON object that strictly follows "
        f"this schema (use 0 for unknown numeric values, empty list [] for unknown lists):\n\n"
        f"{schema_str}\n\n"
        f"Document text:\n{document_text[:6000]}"
    )


async def analyze_financials(
    document_text: str,
    llm_router: Any,
    model: str = "auto",
    api_keys: dict[str, str | None] | None = None,
    provider: str = "openai",
) -> dict[str, Any]:
    """
    Extract structured financial insights from document text.

    Returns a dict with keys:
      - revenue_breakdown  (list of {label, amount})
      - expense_breakdown  (list of {label, amount})
      - key_insights       (list of strings)
      - risk_flags         (list of strings)
      - summary            (string)
    """
    if not document_text or not document_text.strip():
        return _empty_result("No document text provided.")

    resolved_model = (
        model if provider == "bedrock"
        else llm_router.resolve_model(model, "financial analysis", api_keys)
    )
    prompt = _build_prompt(document_text)

    try:
        raw = await llm_router.generate(
            model_name=resolved_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=2048,
            api_keys=api_keys,
            provider=provider,
        )
        result = _parse_json(raw)
        result["model_used"] = resolved_model
        result["skill"] = "financial_analysis"
        return result
    except Exception as exc:
        logger.warning("financial_analysis skill failed: %s", exc)
        fallback = _empty_result(f"Analysis failed: {exc}")
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
        "skill": "financial_analysis",
        "revenue_breakdown": [],
        "expense_breakdown": [],
        "key_insights": [reason],
        "risk_flags": [],
        "summary": reason,
        "model_used": "n/a",
    }
