"""
Enterprise FP&A Scheduled Workflow, Escalation, and Notification Engine.
Manages daily, weekly, and monthly recurring audits, triggers critical alerts, and compiles escalation packages.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid

class ScheduledWorkflowEngine:
    def __init__(self, store: Any, reconciliation_engine: Any, forecaster: Any):
        self.store = store
        self.reconciliation_engine = reconciliation_engine
        self.forecaster = forecaster
        self.workflow_runs: List[Dict[str, Any]] = []

    def execute_recurring_workflow(self, interval: str, starting_cash: float) -> Dict[str, Any]:
        """
        Runs daily, weekly, monthly, or quarterly scheduled operations pipelines.
        """
        run_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # 1. Run audit engines
        recon_res = self.reconciliation_engine.run_reconciliation()
        forecast_res = self.forecaster.generate_driver_forecast(
            starting_cash=starting_cash,
            attendance_rate=0.95,
            ticket_pricing_factor=1.0,
            sponsorship_collection_delay_days=0,
            payroll_growth_rate=0.0,
            transfer_sale_liquidation=0.0,
            vendor_inflation_rate=0.03,
            refinancing_interest_rate=0.05
        )

        metrics_180d = forecast_res["metrics"]["forecast_180d"]
        runway_days = metrics_180d["liquidity_runway_days"]
        burn_rate = metrics_180d["burn_rate"]

        # 2. Trigger Escalation Evaluation
        escalations = []
        alerts = []

        # Runway Risk check
        if runway_days < 90:
            escalations.append({
                "category": "liquidity_runway_critical",
                "severity": "critical",
                "summary": f"Liquidity reserves are projected to deplete within {runway_days} days under current burn velocity.",
                "recomm": "Authorize immediate squad salary overrides or liquid transfers of first-team assets."
            })
            alerts.append({
                "type": "CFO_ALERT",
                "msg": f"CRITICAL: Liquidity reserves runway fallen to {runway_days} days."
            })

        # Covenant Risk check
        has_discrepancy = len(recon_res["discrepancies"]) > 0
        if has_discrepancy:
            escalations.append({
                "category": "covenant_compliance_breach",
                "severity": "high",
                "summary": f"Detected {len(recon_res['discrepancies'])} balance mismatches or missing obligations during validation.",
                "recomm": "Initiate prompt ledger auditing with department heads and creditors."
            })
            alerts.append({
                "type": "TREASURY_ALERT",
                "msg": "WARNING: Balance validation engine identified active financial ledger discrepancies."
            })

        # Overdue Obligations check
        obls = self.store.get_all_obligations()
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        overdue_count = 0
        for o in obls:
            if o.due_date < today_str and o.priority == "high":
                overdue_count += 1

        if overdue_count > 0:
            escalations.append({
                "category": "overdue_obligations_breach",
                "severity": "critical",
                "summary": f"Identified {overdue_count} overdue critical corporate payment obligations.",
                "recomm": "Authorize immediate liquid transfers to avoid legal penalties with HMRC."
            })
            alerts.append({
                "type": "OPERATIONAL_WARNING",
                "msg": f"CRITICAL: {overdue_count} critical payment obligations are overdue."
            })

        # Department budget variance check
        exps = self.store.get_all_expenses()
        overrun_count = sum(1 for e in exps if e.variance < 0)
        if overrun_count > 0:
            alerts.append({
                "type": "DEPARTMENT_VARIANCE_ALERT",
                "msg": f"WARNING: {overrun_count} department budget overruns identified."
            })

        # Record workflow run
        run_record = {
            "run_id": run_id,
            "timestamp": timestamp,
            "interval": interval,
            "reconciliation_integrity": recon_res["formula_integrity_check"],
            "discrepancies_found": len(recon_res["discrepancies"]),
            "runway_days": runway_days,
            "alerts": alerts,
            "escalations": escalations,
            "status": "success"
        }
        self.workflow_runs.append(run_record)

        return run_record

    def get_workflow_history(self) -> List[Dict[str, Any]]:
        return self.workflow_runs
