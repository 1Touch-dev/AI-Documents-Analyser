"""
Refinancing Scenario Skill — simulates debt refinancing with variable interest rates.
"""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

REFINANCING_SCHEMA = {
    "current_annual_interest": 0.0,
    "new_annual_interest": 0.0,
    "annual_savings": 0.0,
    "five_year_savings": 0.0,
    "new_monthly_payment": 0.0,
    "break_even_months": 0,
    "scenarios": [],
    "recommendation": ""
}

SYSTEM_PROMPT = """You are a debt restructuring consultant.
Analyze the refinancing potential based on the document and the target interest rate.
Return ONLY valid JSON matching this schema:
{
  "current_annual_interest": <number>,
  "new_annual_interest": <number>,
  "annual_savings": <number>,
  "five_year_savings": <number>,
  "new_monthly_payment": <number>,
  "break_even_months": <number>,
  "scenarios": [{"rate": <number>, "annual_cost": <number>}],
  "recommendation": "<string>"
}
Return ONLY the JSON. No commentary."""

async def simulate_refinancing(
    document_text: str,
    llm_router: Any,
    target_rate: float = 0.05,
    model: str = "gpt-4o",
    api_keys: dict | None = None,
    provider: str = "openai",
) -> dict:
    from backend.llm_router import _is_bedrock_provider
    resolved_model = model or "gpt-4o"
    
    prompt = (
        f"Simulate a refinancing scenario for the debt found in this document. "
        f"The target new interest rate is {target_rate * 100}%.\n\n"
        f"DOCUMENT:\n{document_text[:8000]}"
    )
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
        
        result = REFINANCING_SCHEMA.copy()
        result.update(data)
        result["skill"] = "refinancing_scenario"
        result["model_used"] = resolved_model
        result["target_rate"] = target_rate
        return result
    except Exception as e:
        logger.warning("Refinancing simulation JSON parse failed: %s", e)
        return {"error": "Failed to parse refinancing data", "raw": raw[:500]}
