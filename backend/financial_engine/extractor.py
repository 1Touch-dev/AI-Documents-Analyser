"""
Financial Extraction Engine
===========================
Extracts structured financial records (revenue, expenses, debt, obligations)
from PDFs, CSVs, and Excel sheets (XLSX, XLSM) using pandas, openpyxl, and LLM parsing.
Stores the extracted records in a normalized financial database schema.
"""

import logging
import json
import re
import io
from typing import Any, Dict, List, Optional
import pandas as pd
import openpyxl
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ─── Normalized Financial Schema Pydantic Models ───

class FinancialEntity(BaseModel):
    name: str
    amount: float
    currency: str = "USD"
    period: str = "FY2025"
    category: str  # e.g., sponsorship, payroll, covenants, etc.
    details: Dict[str, Any] = Field(default_factory=dict)

class ExtractedFinancialData(BaseModel):
    revenue: List[FinancialEntity] = Field(default_factory=list)
    expenses: List[FinancialEntity] = Field(default_factory=list)
    debt: List[FinancialEntity] = Field(default_factory=list)
    obligations: List[FinancialEntity] = Field(default_factory=list)

class FinancialExtractionEngine:
    """Extracts, normalizes, and structures financial data from various files."""

    REVENUE_CATEGORIES = [
        "sponsorship", "ticketing", "memberships", "media_rights",
        "player_sales", "fnb", "merchandise", "partnerships"
    ]

    EXPENSE_CATEGORIES = [
        "payroll", "academy", "stadium", "travel", "legal",
        "technology", "marketing", "vendors"
    ]

    @staticmethod
    def parse_excel_or_csv(file_bytes: bytes, filename: str) -> str:
        """Parse Excel or CSV tables to text/markdown format for LLM processing."""
        try:
            if filename.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(file_bytes))
                return df.to_markdown(index=False)
            else:
                # Excel: parse all sheets
                wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
                sheets_text = []
                for sheet in wb.sheetnames:
                    ws = wb[sheet]
                    data = ws.values
                    cols = next(data) if data else []
                    data = list(data)
                    df = pd.DataFrame(data, columns=cols if cols else None)
                    sheets_text.append(f"### Sheet: {sheet}\n{df.head(100).to_markdown(index=False)}")
                return "\n\n".join(sheets_text)
        except Exception as e:
            logger.error("Failed parsing table %s: %s", filename, e)
            return ""

    @staticmethod
    async def extract_structured_financials(
        text: str,
        filename: str,
        llm_router: Any,
        provider: str = "openai",
        model: str = "gpt-4o",
        api_keys: Optional[Dict] = None
    ) -> ExtractedFinancialData:
        """
        Uses LLM to parse raw text or table data into a strictly normalized financial schema.
        """
        # Truncate text to avoid token limits but keep sufficient detail
        sample_text = text[:120000]

        prompt = f"""You are an enterprise CFO and FP&A expert. Analyze the following document text and extract all structured financial items into a normalized financial schema.

Document Filename: {filename}
Document Content:
---
{sample_text}
---

Your response MUST be a single, valid JSON object following this strict schema:
{{
  "revenue": [
    {{
      "name": "<specific item name, e.g., 'Emirates Shirt Sponsor'>",
      "amount": <float amount, e.g., 15000000.0>,
      "currency": "<ISO currency, e.g., 'USD', 'EUR', 'BRL'>",
      "period": "<fiscal period, e.g., 'Q1 2025', 'FY2025'>",
      "category": "<one of: sponsorship, ticketing, memberships, media_rights, player_sales, fnb, merchandise, partnerships>",
      "details": {{}} // Any extra context (dates, contract length, etc.)
    }}
  ],
  "expenses": [
    {{
      "name": "<specific item name, e.g., 'Squad Salaries'>",
      "amount": <float amount>,
      "currency": "<ISO currency>",
      "period": "<fiscal period>",
      "category": "<one of: payroll, academy, stadium, travel, legal, technology, marketing, vendors>",
      "details": {{}}
    }}
  ],
  "debt": [
    {{
      "name": "<specific item name, e.g., 'Stadium Construction Loan'>",
      "amount": <float amount, principal outstanding>,
      "currency": "<ISO currency>",
      "period": "<maturity period, e.g., '2029-12-31'>",
      "category": "debt",
      "details": {{
         "interest_rate": <float, e.g., 0.055 for 5.5%>,
         "covenants": ["<list of financial covenants, e.g., 'Debt-to-Equity < 1.5'>"],
         "penalties": "<details of breach penalties>",
         "collateral": "<description of collateral>"
      }}
    }}
  ],
  "obligations": [
    {{
      "name": "<specific item name, e.g., 'Unpaid Corporate Taxes'>",
      "amount": <float amount>,
      "currency": "<ISO currency>",
      "period": "<due date, e.g., '2025-06-30'>",
      "category": "obligation",
      "details": {{
         "type": "<one of: taxes, transfer_installments, contracts, bonuses, future_commitments>",
         "priority": "<high | medium | low>"
      }}
    }}
  ]
}}

Rules:
1. Extract ALL details accurately. Only extract items explicitly mentioned or reliably calculated.
2. Ensure amounts are raw floats without commas.
3. Keep the JSON perfectly valid. Do not include markdown code fences (```json) or extra text.
"""

        try:
            raw_response = await llm_router.generate(
                model_name=model,
                messages=[
                    {"role": "system", "content": "You are a professional CFO extracting structured financial intelligence."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=4000,
                provider=provider,
                api_keys=api_keys
            )

            # Clean markdown code fences if LLM includes them
            cleaned = raw_response.strip()
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

            data = json.loads(cleaned)
            return ExtractedFinancialData.model_validate(data)
        except Exception as e:
            logger.error("Financial extraction failed: %s", e)
            # Return empty structure as fallback
            return ExtractedFinancialData()
