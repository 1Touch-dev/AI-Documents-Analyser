"""
Debt Workflow – deep dive into liabilities and refinancing.
"""

from __future__ import annotations
import logging
from typing import Any

logger = logging.getLogger(__name__)

STEPS = [
    "retrieve_documents",
    "analyze_debt",
    "simulate_refinancing",
    "generate_business_insight"
]

OUTPUT_SCHEMA = {
    "debt_analysis": {},
    "refinancing_simulation": {},
    "summary": {
        "total_debt": 0,
        "potential_savings": 0,
        "recommendation": ""
    }
}

async def run(
    input_data: dict[str, Any],
    llm_router: Any,
    provider: str = "openai",
    model: str = "auto",
    api_keys: dict | None = None
) -> dict[str, Any]:
    completed_steps: list[str] = []
    query = input_data.get("query", "Analyze debt and refinancing")
    
    # 1. Retrieve
    from backend.workflows._retriever import retrieve_context
    context = await retrieve_context(query, top_k=10)
    completed_steps.append("retrieve_documents")
    
    # 2. Analyze Debt
    from backend.skills.debt_analysis import analyze_debt
    debt_data = await analyze_debt(context, llm_router, model, api_keys, provider)
    completed_steps.append("analyze_debt")
    
    # 3. Simulate Refinancing
    target_rate = float(input_data.get("target_rate", 0.05))
    from backend.skills.refinancing_scenario import simulate_refinancing
    refi_data = await simulate_refinancing(context, llm_router, target_rate, model, api_keys, provider)
    completed_steps.append("simulate_refinancing")
    
    model_used = debt_data.get("model_used", model)
    
    structured_result = {
        "debt_analysis": debt_data,
        "refinancing_simulation": refi_data,
        "summary": {
            "total_debt": debt_data.get("total_debt", 0),
            "potential_savings": refi_data.get("annual_savings", 0),
            "recommendation": refi_data.get("recommendation", "")
        }
    }

    # 4. Generate Business Insight
    from backend.services.insight_engine import generate_business_insight
    business_insight = await generate_business_insight(
        structured_data=structured_result,
        workflow_type="debt",
        llm_router=llm_router,
        provider=provider,
        model=model_used,
        api_keys=api_keys,
    )
    completed_steps.append("generate_business_insight")

    return {
        "workflow": "debt",
        "steps": completed_steps,
        "result": structured_result,
        "business_insight": business_insight,
        "model_used": model_used,
        "provider": provider
    }

# ── Register ───────────────────────────────────────────────────────────────────
from backend.workflows.workflow_engine import register_workflow

register_workflow("debt", {
    "label": "Debt & Refinancing Analysis",
    "description": "Deep dive into liabilities, interest rates, and refinancing scenarios.",
    "steps": STEPS,
    "output_schema": OUTPUT_SCHEMA,
    "handler": run,
})
