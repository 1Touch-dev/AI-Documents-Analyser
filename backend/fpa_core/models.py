"""
Pydantic models and schemas representing the unified financial ledger
with high-integrity source traceability and lineage.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class SourceLineage(BaseModel):
    """
    Lineage tracking for auditability and explainability.
    Traces every metric back to its source document and context.
    """
    document_id: str = Field(..., description="UUID of the source document")
    document_title: str = Field(..., description="Title of the source file")
    upload_date: str = Field(..., description="Timestamp when the file was ingested")
    spreadsheet_row: Optional[int] = Field(None, description="Row index if extracted from Excel/CSV")
    sheet_name: Optional[str] = Field(None, description="Sheet name if extracted from Excel")
    invoice_number: Optional[str] = Field(None, description="Linked invoice identifier")
    contract_id: Optional[str] = Field(None, description="Linked contract identifier")
    extraction_confidence: float = Field(default=1.0, description="Confidence score of the extraction (0.0 to 1.0)")
    extracted_by: str = Field(default="AI-FP&A Extraction Engine", description="Agent/system that parsed the metric")

class RevenueEntity(BaseModel):
    """
    Normalized Revenue entity with contract details and collection status.
    """
    id: str = Field(..., description="Unique entity ID")
    category: str = Field(..., description="Sponsorship, Ticketing, Retail, Broadcast, etc.")
    amount: float = Field(..., description="Monetary value of the revenue item")
    currency: str = Field(default="USD", description="Currency of the denomination")
    contract_linkage: Optional[str] = Field(None, description="Associated contract ID or name")
    invoice_linkage: Optional[str] = Field(None, description="Associated invoice number")
    expected_payment_date: str = Field(..., description="Expected date of cash inflow")
    collection_status: str = Field(default="pending", description="collected | pending | delayed | disputed")
    counterparty: str = Field(..., description="Payer, sponsor, partner, or ticketing pool")
    lineage: SourceLineage = Field(..., description="Source traceability details")

class ExpenseEntity(BaseModel):
    """
    Normalized Expense entity with department budget comparisons.
    """
    id: str = Field(..., description="Unique entity ID")
    department: str = Field(..., description="F&B, Retail, Marketing, Payroll, Stadium Operations, etc.")
    vendor: str = Field(..., description="Vendor name or supplier")
    recurring: bool = Field(default=True, description="Whether expense is recurring or one-off")
    approval_owner: str = Field(..., description="Department head or approver username")
    budget_line: str = Field(..., description="Specific budget sub-category name")
    allocated_budget: float = Field(..., description="Budget allocated for this line")
    actual_spend: float = Field(..., description="Actual amount spent")
    variance: float = Field(..., description="Allocated budget minus actual spend")
    lineage: SourceLineage = Field(..., description="Source traceability details")

class DebtEntity(BaseModel):
    """
    Normalized Debt entity with covenants and payment schedules.
    """
    id: str = Field(..., description="Unique entity ID")
    principal: float = Field(..., description="Total outstanding debt principal")
    maturity_date: str = Field(..., description="Maturity date of the debt instrument")
    interest_rate: float = Field(..., description="Annual interest rate (decimal, e.g., 0.05)")
    covenants: List[str] = Field(default_factory=list, description="List of restrictive covenants (e.g., Leverage < 4.0)")
    payment_schedule: str = Field(..., description="monthly | quarterly | semi-annually | annually")
    collateral: Optional[str] = Field(None, description="Assets pledged as security")
    restructuring_status: str = Field(default="performing", description="performing | restructured | delinquent")
    creditor: str = Field(..., description="Lending institution or bond pool")
    lineage: SourceLineage = Field(..., description="Source traceability details")

class ObligationEntity(BaseModel):
    """
    Normalized Obligation entity covering future taxes, bonuses, and payroll.
    """
    id: str = Field(..., description="Unique entity ID")
    category: str = Field(..., description="taxes | payroll | bonuses | installments | transfers")
    amount: float = Field(..., description="Future liability or obligation amount")
    due_date: str = Field(..., description="Required payment date")
    priority: str = Field(default="high", description="critical | high | medium | low")
    description: str = Field(..., description="Details regarding the obligation")
    payee: str = Field(..., description="Recipient of the payment")
    lineage: SourceLineage = Field(..., description="Source traceability details")
