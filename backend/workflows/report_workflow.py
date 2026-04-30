"""
Report Workflow
===============
Documents → Metrics Collection → Summary → Recommendations → Report

Steps:
  1. retrieve_documents   — pull relevant chunks from vector store
  2. collect_metrics      — extract key metrics
  3. generate_summary     — executive summary
  4. compile_report       — full structured report output
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

STEPS = [
    "retrieve_documents",
    "collect_metrics",
    "generate_summary",
    "compile_report",
]

OUTPUT_SCHEMA = {
    "title": "",
    "executive_summary": "",
    "key_metrics": {},
    "analysis": [],
    "recommendations": [],
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
            results = vs.search("key metrics summary performance report", top_k=15)
            context = "\n\n".join(r.get("text", "") for r in results)
        except Exception as e:
            logger.warning("Could not retrieve from vector store: %s", e)
            context = "No context provided."
    completed_steps.append("retrieve_documents")
    completed_steps.append("collect_metrics")
    completed_steps.append("generate_summary")

    # ── Steps 2-4: generate full report via skill ──────────────────────────────
    from backend.skills.report_generation import generate_report
    report = await generate_report(
        context=context,
        llm_router=llm_router,
        model=model,
        api_keys=api_keys,
        provider=provider,
    )
    completed_steps.append("compile_report")

    model_used = report.pop("model_used", model)
    report.pop("skill", None)

    return {
        "workflow": "report",
        "steps": completed_steps,
        "result": report,
        "model_used": model_used,
        "provider": provider,
    }


# ── Register ───────────────────────────────────────────────────────────────────
from backend.workflows.workflow_engine import register_workflow  # noqa: E402

register_workflow("report", {
    "label": "Report Generation",
    "description": "Generate a structured executive report with metrics, analysis, and recommendations.",
    "steps": STEPS,
    "output_schema": OUTPUT_SCHEMA,
    "handler": run,
})
