"""
Template Service – manages category-specific KPI structures and templates.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

class TemplateService:
    """Manages business templates and KPIs."""

    TEMPLATES = {
        "Financial": {
            "kpis": [
                "Net Revenue",
                "Gross Margin",
                "EBITDA",
                "Operating Expenses",
                "Net Profit",
                "Cash Flow from Operations",
                "Debt-to-Equity Ratio"
            ],
            "description": "Standard financial analysis template for balance sheets and P&L."
        },
        "F&B": {
            "kpis": [
                "Total F&B Revenue",
                "Average Transaction Value",
                "Cost of Goods Sold (COGS)",
                "Labor Cost %",
                "Waste Percentage",
                "Peak Hour Revenue"
            ],
            "description": "Food and Beverage performance tracking."
        },
        "Ticketing": {
            "kpis": [
                "Total Tickets Sold",
                "Average Ticket Price",
                "Occupancy Rate %",
                "Season Ticket Renewals",
                "Matchday Revenue",
                "No-show Rate"
            ],
            "description": "Stadium ticketing and occupancy analytics."
        },
        "Retail": {
            "kpis": [
                "Total Retail Sales",
                "Sales per Square Meter",
                "Inventory Turnover",
                "Online vs In-store Ratio",
                "Top Selling Categories",
                "Customer Acquisition Cost"
            ],
            "description": "Merchandise and retail store performance."
        },
        "Player Sales": {
            "kpis": [
                "Transfer Revenue",
                "Amortization Expense",
                "Wage-to-Revenue Ratio",
                "Squad Market Value",
                "Academy ROI",
                "Agent Commissions"
            ],
            "description": "Professional sports player transfer and wage analysis."
        },
        "Sponsors": {
            "kpis": [
                "Sponsorship Revenue",
                "Activation Costs",
                "Contract Duration (Avg)",
                "Partner ROI",
                "Exposure Metrics",
                "Renewal Pipeline Value"
            ],
            "description": "Partnership and sponsorship management."
        },
        "Others": {
            "kpis": [
                "General Insight",
                "Summary",
                "Risk Assessment"
            ],
            "description": "Generic business analysis template."
        }
    }

    @staticmethod
    def get_template(category: str) -> dict[str, Any]:
        """Get the template for a specific category."""
        return TemplateService.TEMPLATES.get(category, TemplateService.TEMPLATES["Others"])

    @staticmethod
    def get_all_templates() -> dict[str, Any]:
        """Return all available templates."""
        return TemplateService.TEMPLATES
