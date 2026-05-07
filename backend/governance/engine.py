"""
Governance, Workflows & Vendor Management Engine
================================================
Manages budget approvals, department accountability (variance explanation tracking),
and vendor risks (auto-renewal track, pricing changes, concentration risk index).
Provides expanded audit trails for governance compliance.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class BudgetApproval(BaseModel):
    id: str
    department: str
    amount: float
    purpose: str
    requested_by: str
    approver: str
    status: str  # "pending" | "approved" | "rejected" | "escalated"
    escalation_path: Optional[str] = None
    created_at: str
    approved_at: Optional[str] = None

class DepartmentBudget(BaseModel):
    department: str
    owner: str
    allocated_budget: float
    actual_spend: float
    variance: float
    variance_percentage: float
    variance_explanation: Optional[str] = None

class VendorContract(BaseModel):
    vendor_name: str
    category: str
    annual_spend: float
    contract_duration_months: int
    auto_renew: bool
    pricing_change_last_year: float  # e.g., +0.05 for 5% increase
    concentration_risk_score: float  # e.g., 0.85 (high risk)

class GovernanceEngine:
    """Manages approvals, department accountability, vendor contracts, and audit expansion."""

    @staticmethod
    def calculate_variance(allocated: float, actual: float) -> float:
        return allocated - actual

    @staticmethod
    def evaluate_vendor_risks(contracts: List[VendorContract]) -> Dict[str, Any]:
        """Calculates vendor portfolio risks and concentration indices."""
        if not contracts:
            return {"total_spend": 0.0, "concentration_risk": "low", "warnings": []}

        total_spend = sum(c.annual_spend for c in contracts)
        warnings = []
        max_vendor_spend = 0.0
        max_vendor_name = ""

        auto_renew_count = 0
        pricing_escalation_total = 0.0

        for c in contracts:
            if c.annual_spend > max_vendor_spend:
                max_vendor_spend = c.annual_spend
                max_vendor_name = c.vendor_name
            if c.auto_renew:
                auto_renew_count += 1
            pricing_escalation_total += c.pricing_change_last_year

            # Vendor-specific warning
            if c.concentration_risk_score > 0.8:
                warnings.append(f"HIGH RISK: Vendor '{c.vendor_name}' carries critical concentration risk ({c.concentration_risk_score*100:.0f}%).")

        concentration_pct = (max_vendor_spend / total_spend) if total_spend > 0 else 0.0
        risk_level = "low"
        if concentration_pct > 0.50:
            risk_level = "high"
            warnings.append(f"CONCENTRATION WARNING: '{max_vendor_name}' represents {concentration_pct*100:.1f}% of total vendor spend.")
        elif concentration_pct > 0.25:
            risk_level = "medium"

        avg_price_increase = (pricing_escalation_total / len(contracts)) if contracts else 0.0
        if avg_price_increase > 0.07:
            warnings.append(f"PRICING ESCALATION: Average vendor price increase of {avg_price_increase*100:.1f}% exceeds inflation baseline.")

        return {
            "total_spend": round(total_spend, 2),
            "concentration_ratio": round(concentration_pct, 4),
            "concentration_risk": risk_level,
            "auto_renew_pct": round((auto_renew_count / len(contracts)) * 100, 1) if contracts else 0.0,
            "avg_price_increase": round(avg_price_increase, 4),
            "warnings": warnings
        }

    @staticmethod
    def get_mock_approvals() -> List[BudgetApproval]:
        """Returns mock approval workflow history."""
        return [
            BudgetApproval(
                id="APP-001",
                department="Academy",
                amount=250_000.0,
                purpose="Youth training camp development",
                requested_by="Coach Roberto",
                approver="Admin",
                status="approved",
                created_at="2026-04-10T14:30:00Z",
                approved_at="2026-04-11T09:15:00Z"
            ),
            BudgetApproval(
                id="APP-002",
                department="Marketing",
                amount=75_000.0,
                purpose="Digital campaign subscription expansion",
                requested_by="Sarah Jenkins",
                approver="Admin",
                status="pending",
                created_at="2026-05-02T11:00:00Z"
            ),
            BudgetApproval(
                id="APP-003",
                department="Stadium Operations",
                amount=500_000.0,
                purpose="Roof structure structural repair",
                requested_by="Marco Silva",
                approver="Board",
                status="escalated",
                escalation_path="CFO to Board of Directors",
                created_at="2026-05-04T08:20:00Z"
            )
        ]

    @staticmethod
    def get_mock_departments() -> List[DepartmentBudget]:
        """Returns mock accountability variance statistics."""
        return [
            DepartmentBudget(
                department="Player Payroll",
                owner="Eduardo Gaspar",
                allocated_budget=25_000_000.0,
                actual_spend=26_200_000.0,
                variance=-1_200_000.0,
                variance_percentage=-4.8,
                variance_explanation="Unscheduled contract renewals and mid-season promotion performance bonuses."
            ),
            DepartmentBudget(
                department="Academy",
                owner="Per Mertesacker",
                allocated_budget=5_000_000.0,
                actual_spend=4_800_000.0,
                variance=200_000.0,
                variance_percentage=4.0,
                variance_explanation="Slightly lower travel expense during winter break."
            ),
            DepartmentBudget(
                department="Sponsorship Operations",
                owner="Juliet Vance",
                allocated_budget=1_500_000.0,
                actual_spend=1_450_000.0,
                variance=50_000.0,
                variance_percentage=3.3,
                variance_explanation="Streamlined agency commissions."
            )
        ]

    @staticmethod
    def get_mock_vendors() -> List[VendorContract]:
        """Returns default mock vendor contract roster."""
        return [
            VendorContract(
                vendor_name="GrassMaster Turf",
                category="Stadium Maintenance",
                annual_spend=350_000.0,
                contract_duration_months=24,
                auto_renew=True,
                pricing_change_last_year=0.045,
                concentration_risk_score=0.45
            ),
            VendorContract(
                vendor_name="Global Security Ltd",
                category="Operations",
                annual_spend=1_200_000.0,
                contract_duration_months=36,
                auto_renew=False,
                pricing_change_last_year=0.08,
                concentration_risk_score=0.75
            ),
            VendorContract(
                vendor_name="Nike Merchandise Corp",
                category="Retail",
                annual_spend=4_500_000.0,
                contract_duration_months=60,
                auto_renew=True,
                pricing_change_last_year=0.10,
                concentration_risk_score=0.90
            )
        ]
