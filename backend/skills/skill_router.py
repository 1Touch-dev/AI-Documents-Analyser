"""
Skill Router – dispatches incoming skill requests to the correct skill module.

Supported skills:
  - financial_analysis
  - report_generation
  - consulting_insights
"""

from __future__ import annotations

import logging
from typing import Any

from backend.skills.financial_analysis import analyze_financials
from backend.skills.report_generation import generate_report
from backend.skills.consulting_insights import generate_consulting_insights

logger = logging.getLogger(__name__)

SUPPORTED_SKILLS = {
    "financial_analysis",
    "report_generation",
    "consulting_insights",
}


async def route_skill(
    skill_name: str,
    input_data: dict[str, Any],
    llm_router: Any,
    provider: str = "openai",
) -> dict[str, Any]:
    """
    Route a skill request to the appropriate skill handler.

    Args:
        skill_name:  One of the SUPPORTED_SKILLS keys.
        input_data:  Dict containing at minimum a 'context' or 'document_text' key,
                     plus optional 'model' and API key overrides.
        llm_router:  Shared LLMRouter instance from the FastAPI app.

    Returns:
        Structured JSON-serialisable result dict from the skill.

    Raises:
        ValueError: If skill_name is not recognised.
    """
    if skill_name not in SUPPORTED_SKILLS:
        raise ValueError(
            f"Unknown skill '{skill_name}'. Supported: {sorted(SUPPORTED_SKILLS)}"
        )

    model = input_data.get("model", "auto")
    effective_provider = input_data.get("provider", provider)
    api_keys: dict[str, str | None] = {
        "openai_api_key": input_data.get("openai_api_key"),
        "anthropic_api_key": input_data.get("anthropic_api_key"),
        "gemini_api_key": input_data.get("gemini_api_key"),
        "provider": effective_provider,
    }

    logger.info("Routing skill='%s' model='%s' provider='%s'", skill_name, model, effective_provider)

    if skill_name == "financial_analysis":
        text = input_data.get("document_text") or input_data.get("context", "")
        return await analyze_financials(text, llm_router, model, api_keys, effective_provider)

    if skill_name == "report_generation":
        context = input_data.get("context") or input_data.get("document_text", "")
        return await generate_report(context, llm_router, model, api_keys, effective_provider)

    if skill_name == "consulting_insights":
        context = input_data.get("context") or input_data.get("document_text", "")
        return await generate_consulting_insights(context, llm_router, model, api_keys, effective_provider)

    # Unreachable given the guard above, but keeps type-checkers happy
    raise ValueError(f"Unhandled skill: {skill_name}")
