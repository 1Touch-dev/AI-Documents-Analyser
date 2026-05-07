"""
Driver-Based Forecasting and Variance Recalculation Engine.
Integrates operational drivers, historical variance analysis, and forecast lineages.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid
from backend.fpa_core.persistence import FinancialLedgerStore

class ForecastLineage:
    """
    Audit trail for assumptions, overrides, model versions, and forecast confidences.
    """
    def __init__(self, version: str, assumptions: Dict[str, Any], confidence: float):
        self.forecast_id = str(uuid.uuid4())
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.version = version
        self.assumptions = assumptions
        self.confidence = confidence
        self.logs: List[str] = ["Initial forecast projection created."]

    def add_override(self, field: str, old_val: Any, new_val: Any, user: str):
        self.logs.append(f"Override applied to {field} by {user}: changed from {old_val} to {new_val}")

    def dict(self) -> Dict[str, Any]:
        return {
            "forecast_id": self.forecast_id,
            "created_at": self.created_at,
            "version": self.version,
            "assumptions": self.assumptions,
            "confidence": self.confidence,
            "change_logs": self.logs
        }


class DriverForecastingEngine:
    def __init__(self, store: FinancialLedgerStore):
        self.store = store

    def generate_driver_forecast(
        self,
        starting_cash: float,
        attendance_rate: float,               # e.g., 0.95 (95% full capacity)
        ticket_pricing_factor: float,         # e.g., 1.0 (baseline)
        sponsorship_collection_delay_days: int, # e.g., 30 (delayed days)
        payroll_growth_rate: float,          # e.g., 0.05 (+5%)
        transfer_sale_liquidation: float,     # e.g., 2000000.0 (one-off cash injection)
        vendor_inflation_rate: float,         # e.g., 0.04 (4% inflation)
        refinancing_interest_rate: float,     # e.g., 0.06 (6% interest)
        version: str = "v1.0.0"
    ) -> Dict[str, Any]:
        """
        Simulates future financial cash flows based on operational driver inputs.
        """
        # Load baseline entities
        revs = self.store.get_all_revenues()
        exps = self.store.get_all_expenses()
        debts = self.store.get_all_debts()
        obls = self.store.get_all_obligations()

        # Build Forecast Lineage
        assumptions = {
            "starting_cash": starting_cash,
            "attendance_rate": attendance_rate,
            "ticket_pricing_factor": ticket_pricing_factor,
            "sponsorship_collection_delay_days": sponsorship_collection_delay_days,
            "payroll_growth_rate": payroll_growth_rate,
            "transfer_sale_liquidation": transfer_sale_liquidation,
            "vendor_inflation_rate": vendor_inflation_rate,
            "refinancing_interest_rate": refinancing_interest_rate
        }
        # Confidence calculation based on variance deviations and delay impacts
        confidence = max(0.5, 1.0 - (sponsorship_collection_delay_days / 150.0) - (vendor_inflation_rate * 2.0))
        lineage = ForecastLineage(version, assumptions, confidence)

        # 1. Recalculate Driver-Based Revenue Streams
        total_revenue = 0.0
        for r in revs:
            item_amt = r.amount
            if r.category == "ticketing":
                # Adjusted by attendance and ticketing pricing factors
                item_amt = r.amount * attendance_rate * ticket_pricing_factor
            elif r.category == "sponsorship":
                if sponsorship_collection_delay_days > 45:
                    # High risk of collection haircut
                    item_amt = r.amount * 0.90
            total_revenue += item_amt

        # Include player transfer sales
        total_revenue += transfer_sale_liquidation

        # 2. Recalculate Driver-Based Expenditure Streams
        total_expenditure = 0.0
        for e in exps:
            item_exp = e.actual_spend
            if e.department == "payroll":
                item_exp = e.actual_spend * (1.0 + payroll_growth_rate)
            else:
                # Normal vendor inflation adjustment
                item_exp = e.actual_spend * (1.0 + vendor_inflation_rate)
            total_expenditure += item_exp

        # Debt Service Calculation
        debt_servicing_outflow = 0.0
        for d in debts:
            # Interest payment calculation
            debt_servicing_outflow += d.principal * refinancing_interest_rate / 4.0 # Quarterly interest

        # Scheduled Obligations Inflow/Outflow
        obligations_outflow = sum(o.amount for o in obls)

        # 3. Time Series Recalculation over 30, 60, 90, 180 Days
        periods = [30, 60, 90, 180]
        projections = {}
        current_cash = starting_cash

        for p in periods:
            ratio = p / 360.0
            p_inflow = total_revenue * ratio
            p_outflow = (total_expenditure + debt_servicing_outflow + obligations_outflow) * ratio

            # Delay Cash Collections impact
            if sponsorship_collection_delay_days > 0 and p <= 90:
                p_inflow -= (total_revenue * 0.20) * (sponsorship_collection_delay_days / 90.0)

            p_ending_cash = current_cash + p_inflow - p_outflow
            runway_days = 999
            monthly_burn = max(10000, p_outflow / (p / 30.0))
            if p_outflow > p_inflow:
                runway_days = int((current_cash / monthly_burn) * 30.0)

            # EBITDA approximation
            ebitda = p_inflow - p_outflow + debt_servicing_outflow

            projections[f"forecast_{p}d"] = {
                "days": p,
                "cash_in": p_inflow,
                "cash_out": p_outflow,
                "ending_cash": p_ending_cash,
                "burn_rate": monthly_burn,
                "liquidity_runway_days": min(runway_days, 180 if runway_days < 999 else 999),
                "ebitda": ebitda
            }

        return {
            "lineage": lineage.dict(),
            "metrics": projections,
            "drivers": assumptions
        }


class VarianceEngine:
    """
    Automated variance diagnostics detecting budget deviations, misses, and root causes.
    """
    def __init__(self, store: FinancialLedgerStore):
        self.store = store

    def analyze_variance(self) -> Dict[str, Any]:
        expenses = self.store.get_all_expenses()
        anomalies = []
        total_overrun = 0.0

        for e in expenses:
            if e.actual_spend > e.allocated_budget:
                diff = e.actual_spend - e.allocated_budget
                total_overrun += diff
                pct = (diff / e.allocated_budget) * 100.0 if e.allocated_budget > 0 else 100.0
                anomalies.append({
                    "department": e.department,
                    "budget_line": e.budget_line,
                    "allocated": e.allocated_budget,
                    "actual": e.actual_spend,
                    "overrun_amount": diff,
                    "overrun_percentage": round(pct, 1),
                    "root_cause": f"Unplanned operational cost increases with vendor '{e.vendor}' under owner '{e.approval_owner}'.",
                    "impact_analysis": "Decreases immediate operating margins and accelerates capital reserves consumption velocity."
                })

        return {
            "status": "completed",
            "detected_anomalies_count": len(anomalies),
            "total_overrun_amount": total_overrun,
            "anomalies": anomalies,
            "summary_explanation": f"Detected {len(anomalies)} departmental cost overruns totalling ${total_overrun:,.2f} across facilities."
        }
