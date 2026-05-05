"""
Debt Analysis Skill — extracts and analyzes liabilities and debt structure.
"""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

DEBT_SCHEMA = {
    "total_debt": 0.0,
    "short_term_liabilities": 0.0,
    "long_term_debt": 0.0,
    "creditors": [],
    "interest_rates": [],
    "maturity_profile": [],
    "debt_service_coverage_ratio": 0.0,
    "risks": [],
    "recommendations": []
}

SYSTEM_PROMPT = """You are a debt analysis expert.
Extract all liability and debt information from the document.
Return ONLY valid JSON matching this schema:
{
  "total_debt": <number>,
  "short_term_liabilities": <number>,
  "long_term_debt": <number>,
  "creditors": [{"name": "<string>", "amount": <number>}],
  "interest_rates": [{"debt_type": "<string>", "rate": <number>}],
  "maturity_profile": [{"period": "<string>", "amount": <number>}],
  "debt_service_coverage_ratio": <number>,
  "risks": ["<string>", ...],
  "recommendations": ["<string>", ...]
}
Return ONLY the JSON. No commentary."""

async def analyze_debt(
    document_text: str,
    llm_router: Any,
    model: str = "gpt-4o",
    api_keys: dict | None = None,
    provider: str = "openai",
) -> dict:
    from backend.llm_router import _is_bedrock_provider
    resolved_model = model or "gpt-4o"
    
    prompt = f"Analyze the debt structure in this document:\n\n{document_text[:8000]}"
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
        # Simple extraction
        text = raw.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        data = json.loads(text)
        
        # Basic validation/merging
        result = DEBT_SCHEMA.copy()
        result.update(data)
        result["skill"] = "debt_analysis"
        result["model_used"] = resolved_model
        return result
    except Exception as e:
        logger.warning("Debt analysis JSON parse failed: %s", e)
        return {"error": "Failed to parse debt data", "raw": raw[:500]}
