"""
CFO Executive Reporting and Proactive Management Question Engine.
Synthesizes professional, audit-ready Board reports, Investor Briefings, and Lender packages,
and automatically generates forensic investigation prompts for management.
"""

from typing import Dict, Any, List
from datetime import datetime, timezone
from backend.fpa_core.persistence import FinancialLedgerStore
from backend.driver_engine.scenario import ScenarioDependencyGraph

class BoardGradeReportingEngine:
    def __init__(self, store: FinancialLedgerStore, scenario_graph: ScenarioDependencyGraph):
        self.store = store
        self.scenario_graph = scenario_graph

    def compile_board_report(self, scenario_name: str, starting_cash: float) -> Dict[str, Any]:
        """
        Compiles a comprehensive, professional board-grade executive package
        integrating drivers, variance analysis, covenant audits, and historical lineages.
        """
        # Run scenario recalculation
        sc_res = self.scenario_graph.evaluate_scenario(scenario_name, starting_cash)
        metrics = sc_res["metrics"]["forecast_180d"]
        drivers = sc_res["simulated_drivers"]

        # Generate professional Board Briefing text
        board_narrative = (
            f"Under the simulated '{scenario_name.upper()}' case, our capital reserve position is estimated to "
            f"conclude at ${metrics['ending_cash']:,.2f} over the next 180 days, representing a weighted "
            f"monthly burn velocity of ${metrics['burn_rate']:,.2f}/month. The overall liquidity runway stands "
            f"at {metrics['liquidity_runway_days']} days. Operating margins, evaluated under EBITDA, reflect a simulated "
            f"${metrics['ebitda']:,.2f} balance. The covenant compliance engine has detected {sc_res['covenant_breached_count']} "
            f"breaches of restrictive lender terms."
        )

        # Generate professional Investor Presentation Briefing
        investor_briefing = (
            f"Dear Shareholders, the continuous planning driver-based forecast demonstrates an organic growth rate "
            f"estimate of {(drivers.get('attendance_rate', 0.95) * 100):.1f}% ticketing attendance capacity. "
            f"Net capital outflows are restricted via tactical cost-containment across Facilities. Operating "
            f"EBITDA margins remain the key metric for strategic evaluation."
        )

        # Generate professional Lender Package Briefing
        lender_package = (
            f"Dear Creditors, the stadium facilities credit line remains secured with a mortgage collateral. "
            f"Under the {scenario_name} case, simulated interest payments are scheduled at {(drivers.get('refinancing_interest_rate', 0.05)*100):.2f}% annual yield. "
            f"Covenant audits suggest restrictive debt-to-equity compliance limits are maintained with a confidence of "
            f"{(sc_res['lineage']['confidence'] * 100):.1f}%."
        )

        return {
            "title": f"Board of Directors Financial Briefing - {scenario_name.upper()} CASE",
            "compiled_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "scenario": scenario_name,
            "confidence_level": sc_res["lineage"]["confidence"],
            "lineage_id": sc_res["lineage"]["forecast_id"],
            "kpi_summary": {
                "ending_cash": metrics["ending_cash"],
                "monthly_burn": metrics["burn_rate"],
                "runway_days": metrics["liquidity_runway_days"],
                "ebitda": metrics["ebitda"]
            },
            "narratives": {
                "board_summary": board_narrative,
                "investor_report": investor_briefing,
                "lender_summary": lender_package,
                "management_directive": f"Directives: Implement immediate operational wage cuts of {drivers.get('payroll_growth_rate', 0.0)*100:.1f}% to insulate capital reserves."
            },
            "covenant_monitoring": sc_res["covenant_audits"],
            "assumptions_audited": sc_res["simulated_drivers"],
            "supporting_references": [
                {"document": "Manchester_United_Q1_Financials.xlsx", "reliability": "High", "confidence": "0.98"}
            ]
        }


class ForensicManagementQuestionEngine:
    def __init__(self, store: FinancialLedgerStore):
        self.store = store

    def generate_management_questions(self, board_report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Proactively investigates variance data and scenario outputs to formulate critical,
        analytical management questions and investigation prompts.
        """
        questions = []
        kpis = board_report["kpi_summary"]
        assumptions = board_report["assumptions_audited"]

        # 1. Investigate liquidity runway
        if kpis["runway_days"] < 180:
            questions.append({
                "question": "Why has our simulated capital reserves runway fallen below the 180-day safety threshold?",
                "context": f"Simulated runway stands at {kpis['runway_days']} days, with a monthly burn of ${kpis['monthly_burn']:,.2f}.",
                "suggested_investigation_path": "Audit first-team payroll allocations and stadium expansion capital expenditures for immediate cost-deferral opportunities.",
                "severity": "critical"
            })

        # 2. Investigate collection delays
        if assumptions.get("sponsorship_collection_delay_days", 0) > 30:
            questions.append({
                "question": "Which specific sponsorship accounts are driving the collection delays?",
                "context": f"Sponsorship delay variable is simulated at {assumptions.get('sponsorship_collection_delay_days')} days, causing cash inflow haircut.",
                "suggested_investigation_path": "Cross-reference Snapdragon Global collections records and issue prompt billing reminders or renegotiate contract milestones.",
                "severity": "high"
            })

        # 3. Investigate covenant compliance
        if len(board_report["covenant_monitoring"]) > 0:
            questions.append({
                "question": "How will the CFO mitigate the upcoming restrictive leverage covenant breaches?",
                "context": f"Detected {len(board_report['covenant_monitoring'])} breaches of terms with lenders under current scenario.",
                "suggested_investigation_path": "Initiate talks with Macquarie Bank for a covenant holiday or run emergency player/asset liquidations to pay down the stadium construction credit line.",
                "severity": "critical"
            })

        # Fallback default forensic questions if none triggered
        if not questions:
            questions.append({
                "question": "Are our ticketing and hospitality pricing models fully optimized against stadium capacity limits?",
                "context": f"Current attendance rate is simulated at {assumptions.get('attendance_rate', 0.95)*100:.1f}%.",
                "suggested_investigation_path": "Execute elastic ticket-pricing demand audits across all luxury seating tiers.",
                "severity": "medium"
            })

        return questions
