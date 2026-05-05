"""
Cashflow Analysis Skill — tracks inflows and outflows.
"""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

CASHFLOW_SCHEMA = {
    "operating_cash_flow": 0.0,
    "investing_cash_flow": 0.0,
    "financing_cash_flow": 0.0,
    "net_cash_change": 0.0,
    "major_inflows": [],
    "major_outflows": [],
    "burn_rate": 0.0,
    "runway_months": 0,
    "liquidity_position": "stable",
    "insights": []
}

SYSTEM_PROMPT = """You are a cash flow specialist.
Analyze the cash flows in the provided document.
Return ONLY valid JSON matching this schema:
{
  "operating_cash_flow": <number>,
  "investing_cash_flow": <number>,
  "financing_cash_flow": <number>,
  "net_cash_change": <number>,
  "major_inflows": [{"source": "<string>", "amount": <number>}],
  "major_outflows": [{"item": "<string>", "amount": <number>}],
  "burn_rate": <number>,
  "runway_months": <number>,
  "liquidity_position": "<string>",
  "insights": ["<string>", ...]
}
Return ONLY the JSON. No commentary."""

async def analyze_cashflow(
    document_text: str,
    llm_router: Any,
    model: str = "gpt-4o",
    api_keys: dict | None = None,
    provider: str = "openai",
) -> dict:
    from backend.llm_router import _is_bedrock_provider
    resolved_model = model or "gpt-4o"
    
    prompt = f"Analyze the cash flow in this document:\n\n{document_text[:8000]}"
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]

    raw = await llm_router.generate(
        model_name=resolved_model,
        messages=messages,
        temperature=0.1,
        api_keys=api_keys,
        provider=provider
    )

    try:
        text = raw.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        data = json.loads(text)
        
        result = CASHFLOW_SCHEMA.copy()
        result.update(data)
        result["skill"] = "cashflow_analysis"
        result["model_used"] = resolved_model
        return result
    except Exception as e:
        logger.warning("Cashflow analysis JSON parse failed: %s", e)
        return {"error": "Failed to parse cashflow data", "raw": raw[:500]}
