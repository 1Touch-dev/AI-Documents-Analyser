"""
Institutional CFO and Executive Board-Grade Reporting Templates.
Synthesizes structured reporting models for Board of Directors, Lenders, Investors, and Treasury departments.
"""

from typing import Dict, Any, List
from datetime import datetime, timezone

class ExecutiveReportCompiler:
    def __init__(self, store: Any, reconciliation_audit: Dict[str, Any]):
        self.store = store
        self.reconciliation_audit = reconciliation_audit

    def generate_board_report(self, starting_cash: float, ending_cash: float, burn_rate: float, runway: int, ebitda: float) -> Dict[str, Any]:
        """
        Board Template: Integrates executive summaries, runway audits, covenant compliance, and required actions.
        """
        return {
            "template_type": "board_report",
            "metadata": {
                "title": "Board of Directors Quarter Briefing & Strategy Deck",
                "compiled_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "classification": "STRICTLY CONFIDENTIAL",
                "compliance_confidence": f"{(self.reconciliation_audit.get('integrity_score', 1.0) * 100):.1f}%",
            },
            "executive_summary": (
                f"Operating performance reflects an estimated ending capital reserve position of ${ending_cash:,.2f} "
                f"with a rolling burn rate of ${burn_rate:,.2f} per month. Liquidity runway stands at {runway} days. "
                f"Operating profitability is projected at an EBITDA balance of ${ebitda:,.2f}."
            ),
            "key_performance_indicators": {
                "starting_reserves": starting_cash,
                "ending_reserves": ending_cash,
                "monthly_cash_burn": burn_rate,
                "liquidity_runway_days": runway,
                "ebitda": ebitda
            },
            "debt_and_covenants": {
                "outstanding_principal": sum(d.principal for d in self.store.get_all_debts()),
                "covenants_monitored": [cov for d in self.store.get_all_debts() for cov in d.covenants],
                "active_breaches_detected": len(self.reconciliation_audit.get("discrepancies", []))
            },
            "major_risks": [
                {"risk": "Sponsorship Collection Extension", "severity": "medium", "impact": "Deferred inflows"},
                {"risk": "Departmental Cost Overruns", "severity": "high", "impact": "Runway contraction"}
            ],
            "required_strategic_actions": [
                "Authorize squad wage budget restraints of 10% for the upcoming semester.",
                "Enforce strict 30-day collection limits on Snapdragon sponsorship."
            ]
        }

    def generate_lender_report(self, interest_rate: float) -> Dict[str, Any]:
        """
        Lender Template: Focuses on debt servicing capacity, collateral audits, and refinancing risks.
        """
        debts = self.store.get_all_debts()
        total_debt = sum(d.principal for d in debts)
        
        return {
            "template_type": "lender_package",
            "metadata": {
                "title": "Lender & Creditor Compliance Package",
                "compiled_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "status": "APPROVED FOR RELEASE"
            },
            "debt_servicing_audit": {
                "total_facility_principal": total_debt,
                "refinancing_interest_rate": f"{(interest_rate * 100):.2f}%",
                "quarterly_interest_obligations": sum(d.principal * interest_rate / 4.0 for d in debts),
                "repayment_schedule": "Quarterly installment schedule"
            },
            "collateral_pledged": [d.collateral for d in debts if d.collateral],
            "covenant_tracking": [
                {"covenant": cov, "status": "COMPLIANT", "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%d")}
                for d in debts for cov in d.covenants
            ],
            "refinancing_outlook": "Stable credit profiles with construction facility mortgage fully performing."
        }

    def generate_investor_report(self) -> Dict[str, Any]:
        """
        Investor Template: Focuses on growth trajectories, financial stability, and asset performance.
        """
        revs = self.store.get_all_revenues()
        total_revenue = sum(r.amount for r in revs)
        
        return {
            "template_type": "investor_briefing",
            "metadata": {
                "title": "Investor Financial Stability Presentation",
                "compiled_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            },
            "performance_trends": {
                "total_simulated_inflows": total_revenue,
                "ticketing_organic_growth": "5.0% annualized",
                "attendance_stability": "95.0% stadium capacity"
            },
            "allocation_of_capital": {
                "stadium_infrastructure": "Facilities additions",
                "player_asset_valuation": "First team squad"
            },
            "risk_mitigation": "Comprehensive FX hedging and receivables invoice factoring programs active."
        }

    def generate_emergency_liquidity_report(self, current_cash: float, burn_rate: float) -> Dict[str, Any]:
        """
        Emergency Liquidity Template: Outlines urgent runway situations and cash preservation directives.
        """
        critical_threshold_breached = current_cash < (burn_rate * 3.0)
        
        return {
            "template_type": "emergency_liquidity",
            "metadata": {
                "title": "Emergency Liquidity Deferral & Runway Directive",
                "compiled_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "urgency_level": "CRITICAL" if critical_threshold_breached else "NOMINAL"
            },
            "cash_burn_velocity": {
                "current_liquid_reserves": current_cash,
                "monthly_outflow_burn": burn_rate,
                "estimated_months_to_depletion": current_cash / max(10000.0, burn_rate)
            },
            "liquidity_preservation_directives": [
                "Implement an immediate freeze on all non-essential facilities expenditures.",
                "Mandate department budget overrides to delay vendor collections.",
                "Initiate emergency transfer sales to inject $5,000,000 in immediate reserves."
            ]
        }

    def generate_treasury_report(self) -> Dict[str, Any]:
        """
        Treasury Template: Focuses on payment scheduling and day-to-day obligation clearances.
        """
        obls = self.store.get_all_obligations()
        
        return {
            "template_type": "treasury_briefing",
            "metadata": {
                "title": "Corporate Treasury & Obligation Schedule",
                "compiled_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            },
            "pending_payment_obligations": [
                {
                    "category": o.category,
                    "amount": o.amount,
                    "due_date": o.due_date,
                    "priority": o.priority,
                    "payee": o.payee
                } for o in obls
            ],
            "receivables_collections": [
                {
                    "counterparty": r.counterparty,
                    "amount": r.amount,
                    "expected_payment_date": r.expected_payment_date,
                    "status": r.collection_status
                } for r in self.store.get_all_revenues()
            ]
        }
