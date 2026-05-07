"""
Executive Intelligence & Risk Engine
====================================
Performs automated structural risk detection (liquidity, covenants, tax, budget overruns),
auto-generates critical management Q&As, and synthesizes polished, CFO-grade
executive narratives (board, investor, lender summaries).
"""

import logging
import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class FinancialRisk(BaseModel):
    title: str
    severity: str  # "critical" | "high" | "medium" | "low"
    description: str
    mitigation_action: str

class ManagementQuestion(BaseModel):
    question: str
    context: str
    suggested_investigation_path: str

class ExecutiveNarratives(BaseModel):
    board_summary: str
    investor_report: str
    lender_summary: str
    management_directive: str

class ExecutiveIntelligenceEngine:
    """Detects risks, generates analytical Q&A, and synthesizes executive summaries."""

    @staticmethod
    def run_risk_detection(
        starting_cash: float,
        revenue_items: List[Dict[str, Any]],
        expense_items: List[Dict[str, Any]],
        debt_items: List[Dict[str, Any]],
        obligations: List[Dict[str, Any]],
        burn_rate_monthly: float
    ) -> List[FinancialRisk]:
        """Runs rule-based automated risk checks across parsed entities."""
        risks = []

        # 1. Liquidity Runway risk
        if burn_rate_monthly > 0:
            runway_months = starting_cash / burn_rate_monthly
            if runway_months < 3.0:
                risks.append(FinancialRisk(
                    title="Liquidity Depletion Risk",
                    severity="critical",
                    description=f"Current cash balance (${starting_cash:,.2f}) provides less than 3 months of operational runway (approx. {runway_months:.1f} months) at present burn rates.",
                    mitigation_action="Drawdown existing credit lines, delay non-essential CAPEX, and accelerate collections."
                ))
            elif runway_months < 6.0:
                risks.append(FinancialRisk(
                    title="Moderate Cash Pressure",
                    severity="medium",
                    description=f"Liquidity runway is currently {runway_months:.1f} months, falling short of the ideal 6-month SaaS benchmark.",
                    mitigation_action="Incorporate mild cost containment and review vendor contracts."
                ))

        # 2. Debt Covenant compliance risk
        total_debt = sum(d.get("amount", 0) for d in debt_items)
        total_revenue = sum(r.get("amount", 0) for r in revenue_items)
        if total_revenue > 0 and total_debt > 0:
            debt_to_rev = total_debt / total_revenue
            if debt_to_rev > 1.5:
                risks.append(FinancialRisk(
                    title="Leverage Ratio Covenant Alert",
                    severity="high",
                    description=f"Leverage ratio is {debt_to_rev:.2f}x (total debt to total revenue), placing the company close to common 1.5x restriction boundaries.",
                    mitigation_action="Renegotiate covenants with lenders or consider debt-to-equity restructuring."
                ))

        # 3. Tax / Obligation risk
        tax_total = sum(ob.get("amount", 0) for ob in obligations if "tax" in ob.get("name", "").lower() or ob.get("category") == "taxes")
        if tax_total > 500_000:
            risks.append(FinancialRisk(
                title="Accumulated Tax Liability Exposure",
                severity="high",
                description=f"Unpaid taxes total ${tax_total:,.2f}. Penalties and regulatory enforcement present a high-risk liability.",
                mitigation_action="Set up installment payment programs with tax authorities immediately."
            ))

        # 4. Budget overruns (Expenses higher than revenues)
        total_expenses = sum(e.get("amount", 0) for e in expense_items)
        if total_expenses > total_revenue:
            deficit = total_expenses - total_revenue
            risks.append(FinancialRisk(
                title="Operational Deficit (Budget Overrun)",
                severity="critical",
                description=f"Annualized expenditures exceed revenue by ${deficit:,.2f}. Operating margin is negative.",
                mitigation_action="Enforce strict department budgets and implement a temporary recruitment freeze."
            ))

        # Fallback if no specific risks are triggered
        if not risks:
            risks.append(FinancialRisk(
                title="Sufficient Capitalization",
                severity="low",
                description="The company maintains healthy liquidity reserves and stable debt-to-equity proportions.",
                mitigation_action="Reinvest excess capital into growth-generating initiatives."
            ))

        return risks

    @staticmethod
    def generate_management_questions(
        revenue_items: List[Dict[str, Any]],
        expense_items: List[Dict[str, Any]],
        debt_items: List[Dict[str, Any]]
    ) -> List[ManagementQuestion]:
        """Auto-generates high-value forensic questions for management review."""
        questions = []

        total_expenses = sum(e.get("amount", 0) for e in expense_items)
        payroll_exp = sum(e.get("amount", 0) for e in expense_items if e.get("category") == "payroll")

        if payroll_exp > 0 and total_expenses > 0:
            pct = (payroll_exp / total_expenses) * 100
            if pct > 60:
                questions.append(ManagementQuestion(
                    question="Why is payroll accounting for over 60% of total operational expenditure?",
                    context=f"Payroll expenses total ${payroll_exp:,.2f} out of ${total_expenses:,.2f} ({pct:.1f}%).",
                    suggested_investigation_path="Audit team headcount, review squad contract structures, and analyze performance bonuses."
                ))

        spons_rev = sum(r.get("amount", 0) for r in revenue_items if r.get("category") == "sponsorship")
        total_rev = sum(r.get("amount", 0) for r in revenue_items)

        if spons_rev > 0 and total_rev > 0:
            pct = (spons_rev / total_rev) * 100
            if pct > 40:
                questions.append(ManagementQuestion(
                    question="Which major sponsorship contracts account for the company's high revenue concentration risk?",
                    context=f"Sponsorship revenue totals ${spons_rev:,.2f}, representing {pct:.1f}% of total inbound cash.",
                    suggested_investigation_path="Examine contract expiration dates, auto-renewal terms, and explore ticketing/merchandise diversification."
                ))

        if not questions:
            questions.append(ManagementQuestion(
                question="What is driving our quarterly cost fluctuations?",
                context="Operational expenditures are stable but lack a transparent breakdown by business line.",
                suggested_investigation_path="Review vendor concentration and evaluate auto-renewals."
            ))

        return questions

    @staticmethod
    async def synthesize_executive_narratives(
        starting_cash: float,
        revenue_summary: Dict[str, Any],
        expense_summary: Dict[str, Any],
        forecast_summary: Dict[str, Any],
        risks: List[FinancialRisk],
        llm_router: Any,
        provider: str = "openai",
        model: str = "gpt-4o",
        api_keys: Optional[Dict] = None
    ) -> ExecutiveNarratives:
        """Uses LLM to synthesize narrative summaries for different audiences."""
        prompt = f"""You are an elite, corporate CFO and corporate communications advisor. Synthesize deep, analytical, executive-ready narratives based on the following financial summaries.

FINANCIAL DATA:
- Cash Balance: ${starting_cash:,.2f}
- Revenue breakdown: {json.dumps(revenue_summary)}
- Expense breakdown: {json.dumps(expense_summary)}
- Forecast highlights: {json.dumps(forecast_summary)}
- Detected risks: {json.dumps([r.model_dump() for r in risks])}

Your output MUST be a single, valid JSON object containing exactly these four keys:
{{
  "board_summary": "<A 2-3 paragraph analytical, high-level summary suitable for the Board of Directors. Focus on liquidity, strategy, and risk mitigation.>",
  "investor_report": "<A transparent, growth-focused report for investors detailing EBITDA trends, revenue diversification, and capital efficiency.>",
  "lender_summary": "<A risk-focused, compliance-oriented summary for banks and lenders highlighting debt servicing capabilities, covenants, and collateral preservation.>",
  "management_directive": "<An actionable, operational directive for internal department heads outlining immediate cost-saving targets, collections enforcement, and accountability.>"
}}

Output guidelines:
1. Deliver highly professional, plain-English, executive narratives. Avoid generic filler.
2. Ensure the JSON is completely valid. No markdown syntax or extra text.
"""
        try:
            raw_response = await llm_router.generate(
                model_name=model,
                messages=[
                    {"role": "system", "content": "You are a professional CFO writing corporate communications and narrative reports."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=4000,
                provider=provider,
                api_keys=api_keys
            )

            # Strip markdown
            cleaned = raw_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned.split("```json", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]
            cleaned = cleaned.strip()

            data = json.loads(cleaned)
            return ExecutiveNarratives.model_validate(data)
        except Exception as e:
            logger.error("Narrative synthesis failed: %s", e)
            return ExecutiveNarratives(
                board_summary="Narrative generation unavailable at this moment.",
                investor_report="Narrative generation unavailable at this moment.",
                lender_summary="Narrative generation unavailable at this moment.",
                management_directive="Narrative generation unavailable at this moment."
            )
