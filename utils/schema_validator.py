"""
Schema Validator for LLM Outputs

Ensures highly robust type casting, structure enforcement, and default fallbacks.
Missing values default to 0.0.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

REVENUE_CATEGORIES = [
    "F&B", "Sponsorship", "Tickets", "Retail", "Player Sales", "Other Revenue"
]

EXPENSE_CATEGORIES = [
    "Player Salary", "Coach Salary", "Travel", "Stadium", 
    "Back Office", "Marketing", "Retail", "Misc"
]

def _safe_float(val: Any) -> float:
    """Safely cast varying LLM outputs to floats. Returns 0.0 on failure."""
    if val is None: return 0.0
    if isinstance(val, (int, float)): return float(val)
    try:
        cleaned = str(val).replace(",", "").replace("$", "").replace("€", "").replace("£", "").strip()
        if cleaned.upper().endswith("M"): return float(cleaned[:-1]) * 1_000_000
        if cleaned.upper().endswith("K"): return float(cleaned[:-1]) * 1_000
        return float(cleaned)
    except ValueError:
        return 0.0

def validate_financial_json(raw_json: Dict[str, Any]) -> Dict[str, Any]:
    """Enforce schema shape and defaults to 0.0 for missing data."""
    if not isinstance(raw_json, dict): raw_json = {}

    currency = str(raw_json.get("currency", "USD")).strip().upper()
    if len(currency) != 3: currency = "USD"
        
    fy_val = raw_json.get("fiscal_year")
    fiscal_year = str(fy_val).strip() if fy_val is not None else None
    
    safe_revenue = {}
    safe_expenses = {}
    
    raw_rev = raw_json.get("revenue") or {}
    raw_exp = raw_json.get("expenses") or {}
    
    for cat in REVENUE_CATEGORIES:
        safe_revenue[cat] = _safe_float(raw_rev.get(cat))
    safe_revenue["total"] = _safe_float(raw_rev.get("total")) or sum(safe_revenue.values())
    
    for cat in EXPENSE_CATEGORIES:
        safe_expenses[cat] = _safe_float(raw_exp.get(cat))
    safe_expenses["total"] = _safe_float(raw_exp.get("total")) or sum(safe_expenses.values())
    
    net_result = _safe_float(raw_json.get("net_result"))
    if net_result == 0.0:
        net_result = safe_revenue["total"] - safe_expenses["total"]

    return {
        "currency": currency,
        "fiscal_year": fiscal_year,
        "revenue": safe_revenue,
        "expenses": safe_expenses,
        "net_result": net_result,
        "confidence": str(raw_json.get("confidence", "low")).lower(),
        "notes": str(raw_json.get("notes", "")).strip(),
    }
