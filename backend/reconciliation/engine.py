"""
Enterprise Financial Reconciliation and Data Integrity Engine.
Validates extraction models, conducts cross-document matching, evaluates confidence levels,
and checks system-wide financial integrity.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid
from backend.fpa_core.models import RevenueEntity, ExpenseEntity, DebtEntity, ObligationEntity

class ReconciliationStatus(BaseModel_if_needed=False):
    """
    Data structures representing transaction verification state.
    """
    def __init__(
        self,
        reconciliation_status: str,  # reconciled | discrepancy | partial
        verification_status: str,    # verified | unverified
        source_completeness_score: float, # 0.0 to 1.0
        audit_logs: List[str]
    ):
        self.reconciliation_status = reconciliation_status
        self.verification_status = verification_status
        self.source_completeness_score = source_completeness_score
        self.audit_logs = audit_logs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reconciliation_status": self.reconciliation_status,
            "verification_status": self.verification_status,
            "source_completeness_score": self.source_completeness_score,
            "audit_logs": self.audit_logs
        }


class ReconciliationEngine:
    def __init__(self, store: Any):
        self.store = store

    def run_reconciliation(self) -> Dict[str, Any]:
        """
        Main entrypoint auditing all ledger transactions, cross-document mappings,
        and currency consistencies.
        """
        audit_logs = []
        discrepancies = []
        cross_docs = []
        
        revs = self.store.get_all_revenues()
        exps = self.store.get_all_expenses()
        debts = self.store.get_all_debts()
        obls = self.store.get_all_obligations()

        audit_logs.append(f"Started reconciliation audit at {datetime.now(timezone.utc).isoformat()}")
        audit_logs.append(f"Analyzing {len(revs)} revenues, {len(exps)} expenses, {len(debts)} debts, and {len(obls)} obligations.")

        # 1. Duplicate Transaction Detection
        # Match identical amounts and categories across different IDs
        seen_revs = {}
        for r in revs:
            key = (r.category, r.amount, r.counterparty)
            if key in seen_revs:
                discrepancies.append({
                    "type": "duplicate_revenue",
                    "severity": "medium",
                    "message": f"Possible duplicate revenue identified: Category '{r.category}' of ${r.amount:,.2f} from '{r.counterparty}'.",
                    "entities": [r.id, seen_revs[key].id]
                })
            else:
                seen_revs[key] = r

        seen_exps = {}
        for e in exps:
            key = (e.department, e.actual_spend, e.vendor)
            if key in seen_exps:
                discrepancies.append({
                    "type": "duplicate_expense",
                    "severity": "medium",
                    "message": f"Possible duplicate expense identified: Department '{e.department}' of ${e.actual_spend:,.2f} with vendor '{e.vendor}'.",
                    "entities": [e.id, seen_exps[key].id]
                })
            else:
                seen_exps[key] = e

        # 2. Currency Consistency Checks (Flag anything non-USD)
        for r in revs:
            if r.currency != "USD":
                discrepancies.append({
                    "type": "currency_mismatch",
                    "severity": "high",
                    "message": f"Revenue item '{r.id}' denominated in non-standard currency '{r.currency}'.",
                    "entity": r.id
                })

        # 3. Cross-Document Matching Audits
        # Matching sponsorship revenue expected against actual agreement documents
        for r in revs:
            if r.category == "sponsorship":
                # Look for matching contracts
                if r.contract_linkage:
                    cross_docs.append({
                        "type": "sponsorship_to_agreement",
                        "revenue_id": r.id,
                        "counterparty": r.counterparty,
                        "contract": r.contract_linkage,
                        "matched_by": "contract_linkage_identifier"
                    })
                else:
                    discrepancies.append({
                        "type": "unlinked_sponsorship",
                        "severity": "low",
                        "message": f"Sponsorship revenue from '{r.counterparty}' lacks an audited agreement contract reference.",
                        "entity": r.id
                    })

        # Match expenses to budget owners and approvals
        for e in exps:
            if not e.approval_owner:
                discrepancies.append({
                    "type": "unapproved_expenditure",
                    "severity": "high",
                    "message": f"Expense line '{e.budget_line}' with vendor '{e.vendor}' lacks an authorized approval owner.",
                    "entity": e.id
                })

        # Match debts to scheduled interest obligations
        for d in debts:
            # Find any scheduled obligation that is a tax or interest payment referencing this debt
            has_interest_payment = any(
                "interest" in o.description.lower() or "debt" in o.description.lower()
                for o in obls
            )
            if not has_interest_payment:
                discrepancies.append({
                    "type": "missing_debt_obligation",
                    "severity": "high",
                    "message": f"Outstanding debt principal of ${d.principal:,.2f} with '{d.creditor}' lacks a registered interest service obligation.",
                    "entity": d.id
                })

        # 4. Score Quality & Completeness
        # Calculate source completeness based on lineage fields populated
        scored_items = []
        for r in revs:
            completeness = 0.5
            if r.lineage.spreadsheet_row is not None: completeness += 0.2
            if r.lineage.invoice_number: completeness += 0.15
            if r.lineage.contract_id: completeness += 0.15
            
            reconciled = "reconciled"
            for disc in discrepancies:
                if disc.get("entity") == r.id or r.id in disc.get("entities", []):
                    reconciled = "discrepancy"
                    
            scored_items.append({
                "id": r.id,
                "type": "revenue",
                "completeness": completeness,
                "confidence": r.lineage.extraction_confidence,
                "reconciliation_status": reconciled,
                "verification_status": "verified" if reconciled == "reconciled" else "unverified"
            })

        for e in exps:
            completeness = 0.5
            if e.lineage.spreadsheet_row is not None: completeness += 0.2
            if e.lineage.invoice_number: completeness += 0.15
            if e.lineage.contract_id: completeness += 0.15
            
            reconciled = "reconciled"
            for disc in discrepancies:
                if disc.get("entity") == e.id or e.id in disc.get("entities", []):
                    reconciled = "discrepancy"
                    
            scored_items.append({
                "id": e.id,
                "type": "expense",
                "completeness": completeness,
                "confidence": e.lineage.extraction_confidence,
                "reconciliation_status": reconciled,
                "verification_status": "verified" if reconciled == "reconciled" else "unverified"
            })

        # 5. Financial Integrity Checks
        # Total variance calculations audits
        total_allocated = sum(e.allocated_budget for e in exps)
        total_actual = sum(e.actual_spend for e in exps)
        variance_integrity = "VALID" if round(total_allocated - total_actual, 2) == round(sum(e.variance for e in exps), 2) else "CORRUPTED"
        if variance_integrity == "CORRUPTED":
            discrepancies.append({
                "type": "formula_integrity_breach",
                "severity": "critical",
                "message": "Aggregate budget variance formula does not align with sum of individual department variances.",
            })

        audit_logs.append("Reconciliation audit cycle completed successfully.")
        
        return {
            "status": "completed",
            "audited_at": datetime.now(timezone.utc).isoformat(),
            "discrepancies": discrepancies,
            "cross_document_matches": cross_docs,
            "scored_completeness_registry": scored_items,
            "formula_integrity_check": variance_integrity,
            "audit_logs": audit_logs,
            "integrity_score": max(0.2, 1.0 - (len(discrepancies) * 0.15))
        }
