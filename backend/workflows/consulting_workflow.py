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
    if not context:
        try:
            from backend.vector_store import VectorStore
            vs = VectorStore()
            results = vs.search("business strategy strengths risks opportunities", top_k=15)
            context = "\n\n".join(r.get("text", "") for r in results)
        except Exception as e:
            logger.warning("Could not retrieve from vector store: %s", e)
            context = "No context provided."
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

    return {
        "workflow": "consulting",
        "steps": completed_steps,
        "result": insights,
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
