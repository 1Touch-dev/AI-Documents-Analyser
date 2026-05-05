"""
Insight Engine
==============
Converts structured workflow outputs (raw numbers + lists) into
plain-English business insights that answer:
  1. What happened?
  2. Why does it matter?
  3. What should we do?

Every function returns a strict BusinessInsight dict:
{
  "summary":       "2-3 sentence plain-English overview",
  "key_findings":  ["Finding A", "Finding B", ...],
  "risks":         ["Risk A", "Risk B", ...],
  "recommendations": ["Action A", "Action B", ...]
}

If an LLM is provided, it is used to generate richer language.
If not, a deterministic rule-based engine generates the insight
from the structured data — so the system degrades gracefully.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

INSIGHT_SCHEMA = {
    "summary": "",
    "key_findings": [],
    "risks": [],
    "recommendations": [],
}

# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a senior business analyst translating AI-generated structured data 
into clear, executive-friendly insights.

Your output must be a single JSON object with exactly these keys:
{
  "summary": "<2-3 plain-English sentences: what happened and why it matters>",
  "key_findings": ["<specific, quantified finding>", ...],  // 3-5 items
  "risks": ["<concrete business risk>", ...],               // 2-4 items
  "recommendations": ["<specific, actionable next step>", ...] // 3-5 items
}

Rules:
- Use plain English. No jargon. A CEO with no finance background must understand.
- Every finding must reference at least one number or percentage if available.
- Every recommendation must be specific ("Renegotiate F&B contracts" not "Reduce costs").
- Return ONLY the JSON. No markdown fences, no extra text.
"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not parse insight JSON: {text[:200]}")


def _merge_insight(data: dict) -> dict:
    import copy
    result = copy.deepcopy(INSIGHT_SCHEMA)
    result["summary"] = str(data.get("summary", ""))
    for field in ("key_findings", "risks", "recommendations"):
        if isinstance(data.get(field), list):
            result[field] = [str(x) for x in data[field]]
    return result


# ── Rule-based fallback (no LLM needed) ──────────────────────────────────────

def _financial_rule_based(data: dict) -> dict:
    """Generate insight from financial structured data without LLM."""
    rev = data.get("revenue", {})
    exp = data.get("expenses", {})
    tot = data.get("totals", {})

    total_rev = tot.get("total_revenue") or sum(v for v in rev.values() if isinstance(v, (int, float)))
    total_exp = tot.get("total_expenses") or sum(v for v in exp.values() if isinstance(v, (int, float)))
    net = tot.get("net_profit", total_rev - total_exp)
    margin = tot.get("margin_pct", round(net / total_rev * 100, 1) if total_rev else 0)

    profitable = net >= 0

    # Top revenue source
    top_rev_src = max(rev.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0, default=("unknown", 0))
    # Top expense
    top_exp_src = max(exp.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0, default=("unknown", 0))
    top_exp_pct = round(top_exp_src[1] / total_exp * 100, 0) if total_exp else 0

    existing_insights = data.get("insights", [])
    existing_risks = data.get("risks", [])
    existing_opps = data.get("opportunities", [])

    summary = (
        f"The business generated {'a profit' if profitable else 'a loss'} of "
        f"{abs(net):,.0f} on total revenue of {total_rev:,.0f}, "
        f"achieving a {'positive' if profitable else 'negative'} margin of {margin}%. "
        f"The largest revenue stream is {top_rev_src[0].replace('_', ' ')} "
        f"and the biggest cost is {top_exp_src[0].replace('_', ' ')} at {top_exp_pct:.0f}% of expenses."
    )

    findings = existing_insights[:3] or [
        f"Total revenue: {total_rev:,.0f} | Total expenses: {total_exp:,.0f}",
        f"Net {'profit' if profitable else 'loss'}: {abs(net):,.0f} ({margin}% margin)",
        f"Top cost driver: {top_exp_src[0].replace('_', ' ')} ({top_exp_pct:.0f}% of expenses)",
    ]

    risks = existing_risks[:3] or [
        f"Heavy reliance on {top_rev_src[0].replace('_', ' ')} as primary revenue source creates concentration risk.",
        "If margins are thin, any unexpected cost increase could push the business into loss territory.",
    ]

    recs = existing_opps[:3] or [
        f"Diversify revenue beyond {top_rev_src[0].replace('_', ' ')} to reduce dependency.",
        f"Review {top_exp_src[0].replace('_', ' ')} contracts to identify cost-reduction opportunities.",
        "Set monthly margin targets and review actuals vs. budget quarterly.",
    ]

    return {"summary": summary, "key_findings": findings, "risks": risks, "recommendations": recs}


def _consulting_rule_based(data: dict) -> dict:
    strengths = data.get("strengths", [])
    weaknesses = data.get("weaknesses", [])
    opportunities = data.get("opportunities", [])
    threats = data.get("threats", [])
    actions = data.get("strategic_actions", [])

    summary = (
        f"The SWOT analysis identified {len(strengths)} key strengths and {len(opportunities)} opportunities "
        f"to pursue, alongside {len(threats)} threats and {len(weaknesses)} weaknesses that require attention. "
        f"The strategic priority is to leverage existing strengths to capture the top opportunities "
        f"while mitigating the most critical risks."
    )

    findings = [
        f"Strength: {strengths[0]}" if strengths else "Multiple strengths identified",
        f"Key opportunity: {opportunities[0]}" if opportunities else "Opportunities identified",
        f"Primary threat: {threats[0]}" if threats else "Threats identified",
        f"Critical weakness: {weaknesses[0]}" if weaknesses else "Weaknesses noted",
    ]

    risks_out = threats[:3] if threats else ["External market threats require monitoring"]
    recs_out = actions[:4] if actions else [
        "Execute the top-priority strategic action within 30 days.",
        "Assign clear ownership to each strategic initiative.",
    ]

    return {"summary": summary, "key_findings": findings[:4], "risks": risks_out, "recommendations": recs_out}


def _report_rule_based(data: dict) -> dict:
    title = data.get("title", "Business Report")
    exec_summary = data.get("executive_summary", "")
    metrics = data.get("key_metrics", {})
    analysis = data.get("analysis", [])
    recs = data.get("recommendations", [])

    summary = exec_summary or (
        f"The {title} provides a comprehensive view of business performance. "
        f"{len(metrics)} key metrics were tracked and {len(analysis)} findings were identified. "
        f"A total of {len(recs)} recommendations have been generated to guide next steps."
    )

    findings = analysis[:4] if analysis else [f"{k}: {v}" for k, v in list(metrics.items())[:4]]
    risks_out = [f"Review the recommendation: {r}" for r in recs[:2]] if recs else ["No specific risks flagged"]
    recs_out = recs[:4] if recs else ["Review the full report for actionable next steps."]

    return {"summary": summary, "key_findings": findings, "risks": risks_out, "recommendations": recs_out}


def _debt_rule_based(data: dict) -> dict:
    """Generate insight from debt structured data without LLM."""
    debt_analysis = data.get("debt_analysis", {})
    refi = data.get("refinancing_simulation", {})
    
    total_debt = debt_analysis.get("total_debt", 0)
    savings = refi.get("annual_savings", 0)
    
    summary = (
        f"The business has a total identified debt of {total_debt:,.0f}. "
        f"Based on the current analysis, refinancing could potentially save {savings:,.0f} annually."
    )
    
    findings = [
        f"Total Debt: {total_debt:,.0f}",
        f"Annual Savings Potential: {savings:,.0f}",
        f"Recommendation: {refi.get('recommendation', 'N/A')}"
    ]
    
    return {
        "summary": summary,
        "key_findings": findings,
        "risks": debt_analysis.get("risks", ["Interest rate volatility"]),
        "recommendations": refi.get("recommendations", ["Consider refinancing options"])
    }


# ── LLM-powered insight generation ───────────────────────────────────────────

async def generate_business_insight(
    structured_data: dict,
    workflow_type: str = "financial",
    llm_router=None,
    provider: str = "openai",
    model: str = "auto",
    api_keys: dict | None = None,
) -> dict:
    """
    Convert structured workflow output into plain-English business insight.

    Falls back to rule-based generation if LLM is unavailable.
    """
    # Rule-based fallback (always fast, no cost)
    if workflow_type == "financial":
        fallback = _financial_rule_based(structured_data)
    elif workflow_type == "consulting":
        fallback = _consulting_rule_based(structured_data)
    elif workflow_type == "debt":
        fallback = _debt_rule_based(structured_data)
    else:
        fallback = _report_rule_based(structured_data)

    if llm_router is None:
        logger.info("Insight engine: no LLM router — using rule-based fallback")
        return _merge_insight(fallback)

    # LLM-powered generation
    data_summary = json.dumps(structured_data, indent=2)[:4000]
    prompt = f"""Here is the structured output from a {workflow_type} AI analysis:

{data_summary}

Convert this into plain-English executive insights following the JSON schema exactly."""

    try:
        from backend.llm_router import _is_bedrock_provider
        resolved_model = model
        if model in ("auto", ""):
            resolved_model = "gpt-4o" if not _is_bedrock_provider(provider) else "amazon.nova-lite-v1:0"

        raw = await llm_router.generate(
            model_name=resolved_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
            api_keys=api_keys,
            provider=provider,
        )
        data = _extract_json(raw)
        insight = _merge_insight(data)
        # Ensure we always have content
        if not insight["summary"] or not insight["key_findings"]:
            return _merge_insight(fallback)
        return insight
    except Exception as exc:
        logger.warning("Insight LLM generation failed (%s) — using rule-based fallback", exc)
        return _merge_insight(fallback)


# ── Natural language workflow router ─────────────────────────────────────────

_FINANCIAL_KEYWORDS = {
    "revenue", "profit", "loss", "cost", "expense", "margin", "financial",
    "budget", "money", "salary", "income", "cash", "spend", "roi", "p&l",
    "balance", "invoice", "billing", "pricing", "ticket", "fnb", "sponsorship",
}
_CONSULTING_KEYWORDS = {
    "strategy", "swot", "strengths", "weakness", "opportunity", "threat",
    "consulting", "competitive", "market", "growth", "positioning", "risk",
    "operational", "efficiency", "improvement", "transformation", "change",
}
_REPORT_KEYWORDS = {
    "report", "summary", "overview", "performance", "metrics", "dashboard",
    "analysis", "kpi", "benchmark", "trend", "forecast", "review", "quarter",
    "monthly", "annual", "presentation", "slide", "executive",
}


def classify_query(query: str) -> str:
    """
    Classify a natural-language query to the most appropriate workflow.
    Returns: "financial" | "consulting" | "report"
    """
    q = query.lower()
    words = set(re.findall(r"\b\w+\b", q))

    scores = {
        "financial":  len(words & _FINANCIAL_KEYWORDS),
        "consulting": len(words & _CONSULTING_KEYWORDS),
        "report":     len(words & _REPORT_KEYWORDS),
    }
    best = max(scores, key=lambda k: scores[k])
    if scores[best] == 0:
        # Default: detect intent from question words
        if any(w in q for w in ("how much", "revenue", "profit", "cost", "spend")):
            return "financial"
        if any(w in q for w in ("strategy", "advice", "recommend", "improve")):
            return "consulting"
        return "report"
    return best
