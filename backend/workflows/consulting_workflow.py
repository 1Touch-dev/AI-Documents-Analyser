"""
Consulting Workflow
===================
Documents → Context Analysis → SWOT → Strategic Actions → Output

Steps:
  1. retrieve_documents   — pull relevant chunks from vector store
  2. swot_analysis        — strengths, weaknesses, opportunities, threats
  3. strategic_planning   — prioritised strategic actions
  4. compile_output       — merge all into final consulting brief
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

STEPS = [
    "retrieve_documents",
    "swot_analysis",
    "strategic_planning",
    "compile_output",
    "generate_business_insight",
]

OUTPUT_SCHEMA = {
    "strengths": [],
    "weaknesses": [],
    "opportunities": [],
    "threats": [],
    "strategic_actions": [],
}


async def run(
    input_data: dict,
    llm_router,
    provider: str = "openai",
    model: str = "auto",
    api_keys: dict | None = None,
) -> dict:
    completed_steps: list[str] = []

    # ── Step 1: retrieve documents ─────────────────────────────────────────────
    context = input_data.get("context") or input_data.get("document_text", "")
    if not context.strip():
        from backend.workflows._retriever import retrieve_context
        context = await retrieve_context(
            "business strategy strengths weaknesses risks opportunities competitive market",
            top_k=15,
        )
    completed_steps.append("retrieve_documents")

    # ── Step 2+3: SWOT + strategic actions via skill ───────────────────────────
    from backend.skills.consulting_insights import generate_consulting_insights
    insights = await generate_consulting_insights(
        context=context,
        llm_router=llm_router,
        model=model,
        api_keys=api_keys,
        provider=provider,
    )
    completed_steps.append("swot_analysis")
    completed_steps.append("strategic_planning")

    # ── Step 4: compile ────────────────────────────────────────────────────────
    completed_steps.append("compile_output")

    model_used = insights.pop("model_used", model)
    insights.pop("skill", None)

    from backend.services.insight_engine import generate_business_insight
    business_insight = await generate_business_insight(
        structured_data=insights,
        workflow_type="consulting",
        llm_router=llm_router,
        provider=provider,
        model=model_used,
        api_keys=api_keys,
    )
    completed_steps.append("generate_business_insight")

    return {
        "workflow": "consulting",
        "steps": completed_steps,
        "result": insights,
        "business_insight": business_insight,
        "model_used": model_used,
        "provider": provider,
    }


# ── Register ───────────────────────────────────────────────────────────────────
from backend.workflows.workflow_engine import register_workflow  # noqa: E402

register_workflow("consulting", {
    "label": "Consulting Analysis",
    "description": "SWOT analysis and strategic action plan based on indexed documents.",
    "steps": STEPS,
    "output_schema": OUTPUT_SCHEMA,
    "handler": run,
})
