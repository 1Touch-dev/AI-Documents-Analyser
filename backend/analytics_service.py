"""
Financial Analytics Service – LLM-driven structured extraction of revenue
and expense data from document text.

Unlike the pattern-based AnalyticsEngine, this service uses a local LLM
(Gemma 4 E2B) to understand context and return structured JSON financial data.

Categories
----------
Revenue:  F&B, Sponsorship, Tickets, Retail, Player Sales, Other Revenue
Expenses: Player Salary, Coach Salary, Travel, Stadium, Back Office,
          Marketing, Retail, Misc

Usage
-----
    svc = FinancialAnalyticsService(llm_router)
    report = await svc.extract_financials(doc_id, doc_text, db)
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from config.settings import settings
from db.models import FinancialReport, FinancialMetric, AnalyticsJob
from utils.schema_validator import validate_financial_json, REVENUE_CATEGORIES, EXPENSE_CATEGORIES

if TYPE_CHECKING:
    from backend.llm_router import LLMRouter

logger = logging.getLogger(__name__)

# Revenue and Expense categories are imported from utils.schema_validator

# ── Extraction prompt ─────────────────────────────────────────────────────────
_EXTRACTION_PROMPT = """You are a financial data extraction specialist. Analyze the following document text and extract structured financial data.

Return a JSON object with EXACTLY this structure (do not add extra fields):
{{
  "currency": "USD",
  "fiscal_year": null,
  "revenue": {{
    "F&B": null,
    "Sponsorship": null,
    "Tickets": null,
    "Retail": null,
    "Player Sales": null,
    "Other Revenue": null,
    "total": null
  }},
  "expenses": {{
    "Player Salary": null,
    "Coach Salary": null,
    "Travel": null,
    "Stadium": null,
    "Back Office": null,
    "Marketing": null,
    "Retail": null,
    "Misc": null,
    "total": null
  }},
  "net_result": null,
  "confidence": "low",
  "notes": ""
}}

Rules:
- Use null for categories where no data is found.
- All monetary values must be plain numbers (no symbols, no commas). Use millions as base unit (e.g., 1500000 not 1.5M).
- Set "currency" to the ISO code detected (e.g., "USD", "BRL", "EUR").
- Set "confidence" to "high", "medium", or "low" based on data quality.
- In "notes", briefly describe what financial data was found or not found.
- Return ONLY the JSON object — no preamble, no explanation.

Document Text:
{text}

JSON Output:"""


class FinancialAnalyticsService:
    """
    LLM-driven financial data extractor.

    Parameters
    ----------
    llm_router : LLMRouter
        Shared LLM router instance for calling the extraction model.
    """

    def __init__(self, llm_router: "LLMRouter") -> None:
        self._llm = llm_router

    async def extract_financials(
        self,
        doc_id: str,
        doc_text: str,
        db: Session,
        doc_title: str = "",
        overwrite: bool = False,
        job_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Run LLM-based financial extraction for a document and persist to DB.

        Parameters
        ----------
        doc_id : str
            UUID of the document.
        doc_text : str
            Full (or sampled) text from the document.
        db : Session
            Active SQLAlchemy session.
        doc_title : str
            Document title for logging.
        overwrite : bool
            If True, overwrite existing report for this doc_id.

        Returns
        -------
        dict
            Parsed financial data + metadata.
        """
        # Check for existing report
        existing = db.query(FinancialReport).filter(
            FinancialReport.doc_id == doc_id
        ).first()

        if existing and not overwrite:
            logger.info("Financial report already exists for doc %s, skipping.", doc_id)
            return self._report_to_dict(existing)

        # Trim text to avoid token limits (first 12,000 chars is usually sufficient)
        text_sample = doc_text[:12_000]

        # Build prompt
        prompt = _EXTRACTION_PROMPT.format(text=text_sample)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a precise financial data extraction AI. "
                    "Always return valid JSON only."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        raw_json: dict[str, Any] = {}
        model_used = settings.financial_extraction_model

        try:
            import asyncio
            # Timeout control (30s) per task requirement
            answer, model_used = await asyncio.wait_for(
                self._llm.generate_with_fallback(
                    preferred_model=settings.financial_extraction_model,
                    messages=messages,
                    temperature=0.0,
                    max_tokens=1024,
                ),
                timeout=30.0
            )
            raw_json = self._parse_json_response(answer)
        except asyncio.TimeoutError:
            logger.error("Financial extraction timed out for doc %s", doc_id)
            if job_id:
                db.query(AnalyticsJob).filter(AnalyticsJob.id == job_id).update({
                    "error_message": "LLM extraction timed out (30s)"
                })
                db.commit()
            raw_json = self._empty_report()
        except Exception as e:
            logger.error(
                "Financial extraction failed for doc %s (%s): %s", doc_id, doc_title, e
            )
            raw_json = self._empty_report()

        # Persist to database
        if existing and overwrite:
            existing.revenue = raw_json.get("revenue", {})
            existing.expenses = raw_json.get("expenses", {})
            existing.currency = raw_json.get("currency", "USD")
            existing.fiscal_year = raw_json.get("fiscal_year")
            existing.net_result = raw_json.get("net_result")
            existing.confidence = raw_json.get("confidence", "low")
            existing.notes = raw_json.get("notes", "")
            existing.model_used = model_used
            existing.extracted_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(existing)
            return self._report_to_dict(existing)
        else:
            report = FinancialReport(
                doc_id=doc_id,
                doc_title=doc_title,
                revenue=raw_json.get("revenue", {}),
                expenses=raw_json.get("expenses", {}),
                currency=raw_json.get("currency", "USD"),
                fiscal_year=raw_json.get("fiscal_year"),
                net_result=raw_json.get("net_result"),
                confidence=raw_json.get("confidence", "low"),
                notes=raw_json.get("notes", ""),
                model_used=model_used,
            )
            db.add(report)
            db.commit()
            db.refresh(report)

        # Sync to FinancialMetric table for granular analytical queries
        self._sync_metrics(doc_id, raw_json, db)

        return self._report_to_dict(report)

    def _sync_metrics(self, doc_id: str, raw_json: dict, db: Session):
        """Flat save categories to financial_metrics for efficient dashboard queries."""
        # First clear old metrics if they exist for this doc
        db.query(FinancialMetric).filter(FinancialMetric.doc_id == doc_id).delete()
        
        currency = raw_json.get("currency", "USD")
        fy = raw_json.get("fiscal_year")
        
        # Revenue
        revs = raw_json.get("revenue", {})
        for cat, val in revs.items():
            if val is not None and cat != "total":
                m = FinancialMetric(
                    doc_id=doc_id, category=cat, value=float(val), 
                    type="revenue", currency=currency, fiscal_year=fy
                )
                db.add(m)
        
        # Expenses
        exps = raw_json.get("expenses", {})
        for cat, val in exps.items():
            if val is not None and cat != "total":
                m = FinancialMetric(
                    doc_id=doc_id, category=cat, value=float(val), 
                    type="expense", currency=currency, fiscal_year=fy
                )
                db.add(m)
        
        db.commit()

    def _parse_json_response(self, raw: str) -> dict[str, Any]:
        """
        Robustly extract JSON from LLM response, even if wrapped in markdown.
        """
        # Strip markdown code fences
        cleaned = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
        # Find the first {...} block
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        raw_dict = {}
        if match:
            try:
                raw_dict = json.loads(match.group(0))
            except json.JSONDecodeError as e:
                logger.warning("JSON parse failed: %s\nRaw: %s", e, raw[:500])
        
        # Robust validation with fallback to 0.0
        return validate_financial_json(raw_dict)

    @staticmethod
    def _empty_report() -> dict[str, Any]:
        """Return a zero-filled financial report structure."""
        return validate_financial_json({})

    @staticmethod
    def _report_to_dict(report: FinancialReport) -> dict[str, Any]:
        return {
            "id": str(report.id),
            "doc_id": report.doc_id,
            "doc_title": report.doc_title,
            "currency": report.currency,
            "fiscal_year": report.fiscal_year,
            "revenue": report.revenue,
            "expenses": report.expenses,
            "net_result": report.net_result,
            "confidence": report.confidence,
            "notes": report.notes,
            "model_used": report.model_used,
            "extracted_at": report.extracted_at.isoformat() if report.extracted_at else None,
        }

    def get_all_reports(self, db: Session) -> list[dict[str, Any]]:
        """Fetch all stored financial reports."""
        reports = db.query(FinancialReport).order_by(
            FinancialReport.extracted_at.desc()
        ).all()
        return [self._report_to_dict(r) for r in reports]

    def get_export_data(self, db: Session) -> list[dict[str, Any]]:
        """
        Return flattened records suitable for CSV / Tableau export.
        Each row is a doc + one revenue/expense line item.
        """
        reports = db.query(FinancialReport).all()
        rows: list[dict[str, Any]] = []

        for r in reports:
            base = {
                "doc_id": r.doc_id,
                "doc_title": r.doc_title,
                "currency": r.currency,
                "fiscal_year": r.fiscal_year,
                "confidence": r.confidence,
                "model_used": r.model_used,
                "extracted_at": r.extracted_at.isoformat() if r.extracted_at else None,
            }
            # Revenue rows
            for cat, amount in (r.revenue or {}).items():
                rows.append({
                    **base,
                    "type": "Revenue",
                    "category": cat,
                    "amount": amount,
                })
            # Expense rows
            for cat, amount in (r.expenses or {}).items():
                rows.append({
                    **base,
                    "type": "Expense",
                    "category": cat,
                    "amount": amount,
                })

        return rows
