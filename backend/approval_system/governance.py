"""
Governance, Approvals, and Departmental Review Workflow Engine.
Manages approval lifecycles, departmental variance reviews, and registers forecast overrides.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid

class ApprovalAction:
    """
    Structured model tracking approval actions.
    """
    def __init__(self, approver: str, status: str, notes: str, escalation_level: int = 0):
        self.approver = approver
        self.status = status # approved | rejected | escalated
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.notes = notes
        self.escalation_level = escalation_level

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approver": self.approver,
            "status": self.status,
            "timestamp": self.timestamp,
            "notes": self.notes,
            "escalation_level": self.escalation_level
        }


class ApprovalLifecycleTracker:
    def __init__(self):
        # Maps budget_line_id or entity_id to its approval actions history
        self.registry: Dict[str, List[Dict[str, Any]]] = {}

    def submit_for_approval(self, entity_id: str, requester: str, amount: float) -> Dict[str, Any]:
        initial_action = {
            "action_id": str(uuid.uuid4()),
            "requester": requester,
            "amount": amount,
            "status": "pending_approval",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "history": []
        }
        self.registry[entity_id] = [initial_action]
        return initial_action

    def record_decision(self, entity_id: str, approver: str, status: str, notes: str, escalation_level: int = 0) -> Optional[Dict[str, Any]]:
        if entity_id not in self.registry:
            return None
        
        history_entry = ApprovalAction(approver, status, notes, escalation_level).to_dict()
        current_record = self.registry[entity_id][0]
        current_record["status"] = status
        current_record["history"].append(history_entry)
        return current_record


class DepartmentReviewCycle:
    def __init__(self):
        # Maps department names to their active owners, reviews, and explanations
        self.reviews: Dict[str, Dict[str, Any]] = {
            "payroll": {
                "owner": "Dan Ashworth",
                "monthly_status": "reviewed",
                "variance_explanation": "Squad wages fully aligned with first-team agreements. No variances detected.",
                "audited_at": datetime.now(timezone.utc).strftime("%Y-%m-%d")
            },
            "stadium": {
                "owner": "Collette Roche",
                "monthly_status": "under_review",
                "variance_explanation": "Stadium facilities cost overrun driven by emergency Old Trafford roofing repairs.",
                "audited_at": datetime.now(timezone.utc).strftime("%Y-%m-%d")
            }
        }

    def get_department_reviews(self) -> Dict[str, Dict[str, Any]]:
        return self.reviews

    def submit_variance_explanation(self, department: str, owner: str, explanation: str) -> Dict[str, Any]:
        self.reviews[department] = {
            "owner": owner,
            "monthly_status": "reviewed",
            "variance_explanation": explanation,
            "audited_at": datetime.now(timezone.utc).strftime("%Y-%m-%d")
        }
        return self.reviews[department]


class WorkflowGovernanceLogger:
    def __init__(self):
        self.logs: List[Dict[str, Any]] = []

    def log_governance_event(self, event_type: str, actor: str, description: str, details: Dict[str, Any]):
        entry = {
            "log_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type, # model_override | forecast_change | agent_decision | workflow_failure
            "actor": actor,
            "description": description,
            "details": details
        }
        self.logs.append(entry)
        return entry

    def get_governance_logs(self) -> List[Dict[str, Any]]:
        return self.logs
