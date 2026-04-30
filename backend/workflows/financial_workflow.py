"""
Financial Workflow
==================
Documents → Financial Extraction → Analysis → Risk/Opportunity Insights → Output

Steps:
  1. retrieve_documents   — pull relevant chunks from vector store
  2. extract_financials   — structured revenue + expense extraction
  3. calculate_totals     — compute totals, margins, ratios
  4. generate_insights    — risks and opportunities via LLM
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

STEPS = [
    "retrieve_documents",
    "extract_financials",
    "calculate_totals",
    "generate_insights",
]

OUTPUT_SCHEMA = {
    "revenue": {"fnb": 0, "sponsorship": 0, "tickets": 0, "retail": 0, "player_sales": 0},
    "expenses": {"player_salary": 0, "coach_salary": 0, "travel": 0, "stadium": 0, "retail": 0, "fnb": 0, "back_office": 0, "misc": 0},
    "totals": {"total_revenue": 0, "total_expenses": 0, "net_profit": 0, "margin_pct": 0},
    "insights": [],
    "risks": [],
    "opportunities": [],
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
    document_text = input_data.get("document_text") or input_data.get("context", "")
    if not document_text:
        # Try to pull from vector store if available
        try:
            from backend.vector_store import VectorStore
            vs = VectorStore()
            results = vs.search("financial revenue expenses profit", top_k=15)
            document_text = "\n\n".join(r.get("text", "") for r in results)
        except Exception as e:
            logger.warning("Could not retrieve from vector store: %s", e)
            document_text = "No document text provided."
    completed_steps.append("retrieve_documents")

    # ── Step 2: extract financials via skill ───────────────────────────────────
    from backend.skills.financial_analysis import analyze_financials
    financial_data = await analyze_financials(
        document_text=document_text,
        llm_router=llm_router,
        model=model,
        api_keys=api_keys,
        provider=provider,
    )
    completed_steps.append("extract_financials")

    # ── Step 3: calculate totals ───────────────────────────────────────────────
    rev = financial_data.get("revenue", {})
    exp = financial_data.get("expenses", {})
    total_revenue = sum(v for v in rev.values() if isinstance(v, (int, float)))
    total_expenses = sum(v for v in exp.values() if isinstance(v, (int, float)))
    net_profit = total_revenue - total_expenses
    margin_pct = round((net_profit / total_revenue * 100), 2) if total_revenue else 0
    totals = {
        "total_revenue": round(total_revenue, 2),
        "total_expenses": round(total_expenses, 2),
        "net_profit": round(net_profit, 2),
        "margin_pct": margin_pct,
    }
    completed_steps.append("calculate_totals")

    # ── Step 4: insights already embedded in financial_data ───────────────────
    completed_steps.append("generate_insights")

    model_used = financial_data.pop("model_used", model)
    financial_data.pop("skill", None)

    return {
        "workflow": "financial",
        "steps": completed_steps,
        "result": {
            **financial_data,
            "totals": totals,
        },
        "model_used": model_used,
        "provider": provider,
    }


# ── Register ───────────────────────────────────────────────────────────────────
from backend.workflows.workflow_engine import register_workflow  # noqa: E402

register_workflow("financial", {
    "label": "Financial Analysis",
    "description": "Extract revenue, expenses, totals, margins, risks and opportunities from indexed documents.",
    "steps": STEPS,
    "output_schema": OUTPUT_SCHEMA,
    "handler": run,
})
