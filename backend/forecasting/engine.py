"""
Forecasting & Scenario Engine
=============================
Simulates forward-looking business intelligence forecasts (30, 60, 90, 180 days)
based on dynamic scenario assumptions (Base, Optimistic, Downside, Emergency).
Calculates live cash flows, burn rates, runway, EBITDA trends, and debt service pressure.
"""

import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class ScenarioAssumptions(BaseModel):
    sponsorship_change_pct: float = 0.0      # e.g. -0.15 for 15% reduction
    payroll_change_pct: float = 0.0          # e.g. -0.10 for 10% reduction
    refinancing_rate: float = 0.055          # e.g. 5.5% interest rate
    transfer_sales: float = 0.0              # additional cash from sales
    delayed_collections_pct: float = 0.0     # % of collections delayed
    revenue_growth_pct: float = 0.05         # default 5% annual growth
    inflation_pct: float = 0.03              # default 3% annual inflation
    relegation_or_promotion: str = "none"    # "relegation" | "promotion" | "none"

class ForecastPeriod(BaseModel):
    days: int
    cash_in: float
    cash_out: float
    net_cash_flow: float
    ending_cash: float
    burn_rate: float
    liquidity_runway_days: float
    ebitda: float
    debt_servicing_pressure: str  # "high" | "medium" | "low"

class ScenarioForecastResult(BaseModel):
    scenario: str  # "base" | "optimistic" | "downside" | "emergency"
    assumptions: ScenarioAssumptions
    forecast_30d: ForecastPeriod
    forecast_60d: ForecastPeriod
    forecast_90d: ForecastPeriod
    forecast_180d: ForecastPeriod
    ebitda_trend: List[float]
    warnings: List[str]

class ForecastingScenarioEngine:
    """Orchestrates interactive cash flow and financial scenario modeling."""

    @staticmethod
    def calculate_forecast(
        starting_cash: float,
        revenue_items: List[Dict[str, Any]],
        expense_items: List[Dict[str, Any]],
        debt_items: List[Dict[str, Any]],
        obligations: List[Dict[str, Any]],
        assumptions: ScenarioAssumptions,
        scenario_name: str = "base"
    ) -> ScenarioForecastResult:
        """
        Calculates dynamic financial forecasts (30, 60, 90, 180 days) based on
        real financial records and interactive assumptions.
        """
        # Sum baseline daily revenues and expenses
        total_rev_annual = sum(item.get("amount", 0) for item in revenue_items)
        total_exp_annual = sum(item.get("amount", 0) for item in expense_items)
        
        # If no items provided, use standard default baselines
        if total_rev_annual == 0:
            total_rev_annual = 50_000_000.0
        if total_exp_annual == 0:
            total_exp_annual = 45_000_000.0

        # Apply Scenario Factor Adjustments (Shift baselines according to scenario name)
        factor_rev = 1.0
        factor_exp = 1.0
        
        if scenario_name == "optimistic":
            factor_rev = 1.15
            factor_exp = 0.95
        elif scenario_name == "downside":
            factor_rev = 0.80
            factor_exp = 1.05
        elif scenario_name == "emergency":
            factor_rev = 0.60
            factor_exp = 1.10

        # Apply Assumption Sliders
        rev_multiplier = factor_rev * (1.0 + assumptions.revenue_growth_pct)
        exp_multiplier = factor_exp * (1.0 + assumptions.inflation_pct)

        # Sponsorship specific slider
        adjusted_rev_annual = 0.0
        for item in revenue_items:
            amt = item.get("amount", 0)
            if item.get("category") == "sponsorship":
                adjusted_rev_annual += amt * (1.0 + assumptions.sponsorship_change_pct) * rev_multiplier
            else:
                adjusted_rev_annual += amt * rev_multiplier
        if adjusted_rev_annual == 0:
            adjusted_rev_annual = total_rev_annual * rev_multiplier

        # Payroll specific slider
        adjusted_exp_annual = 0.0
        for item in expense_items:
            amt = item.get("amount", 0)
            if item.get("category") == "payroll":
                adjusted_exp_annual += amt * (1.0 + assumptions.payroll_change_pct) * exp_multiplier
            else:
                adjusted_exp_annual += amt * exp_multiplier
        if adjusted_exp_annual == 0:
            adjusted_exp_annual = total_exp_annual * exp_multiplier

        # Relegation impact
        if assumptions.relegation_or_promotion == "relegation":
            adjusted_rev_annual *= 0.65  # 35% revenue drop
        elif assumptions.relegation_or_promotion == "promotion":
            adjusted_rev_annual *= 1.40  # 40% revenue boost

        # Daily rates
        daily_rev = (adjusted_rev_annual / 365.0) * (1.0 - assumptions.delayed_collections_pct)
        daily_exp = (adjusted_exp_annual / 365.0)

        # Extra one-time injection from player/transfer sales
        one_time_cash_injection = assumptions.transfer_sales

        # Debt servicing calculations
        annual_debt_servicing = 0.0
        total_debt_principal = sum(d.get("amount", 0) for d in debt_items)
        for debt in debt_items:
            principal = debt.get("amount", 0)
            details = debt.get("details", {})
            # Refinancing rate override
            rate = assumptions.refinancing_rate if assumptions.refinancing_rate else details.get("interest_rate", 0.05)
            annual_debt_servicing += principal * rate

        if annual_debt_servicing == 0 and total_debt_principal > 0:
            annual_debt_servicing = total_debt_principal * assumptions.refinancing_rate

        daily_debt_service = annual_debt_servicing / 365.0

        # Generate Forecast Periods
        periods = [30, 60, 90, 180]
        forecast_periods = {}
        ebitda_trend = []
        warnings = []

        current_cash = starting_cash if starting_cash > 0 else 5_000_000.0

        for days in periods:
            # Cash in/out
            cash_in = (daily_rev * days) + (one_time_cash_injection if days == 30 else 0)
            cash_out = (daily_exp * days) + (daily_debt_service * days)
            
            # Obligations due within this period
            obligations_due = 0.0
            for ob in obligations:
                # Mock parsing due dates or checking period
                amt = ob.get("amount", 0)
                details = ob.get("details", {})
                priority = details.get("priority", "medium")
                # Higher priority obligations are simulated as paid sooner
                if priority == "high" and days >= 30:
                    obligations_due += amt / 4.0
                elif days >= 90:
                    obligations_due += amt / 2.0

            cash_out += obligations_due

            net_cash_flow = cash_in - cash_out
            ending_cash = max(0.0, current_cash + net_cash_flow)
            
            # Monthly burn rate
            burn_rate = max(0.0, cash_out - cash_in) / (days / 30.0)
            
            # Liquidity runway in days
            if burn_rate > 0:
                runway = (ending_cash / burn_rate) * 30.0
            else:
                runway = 999.0  # Safe/Infinite runway

            # EBITDA = revenue - expenses
            ebitda = (daily_rev * days) - (daily_exp * days)
            ebitda_trend.append(ebitda)

            # Debt servicing pressure assessment
            pressure = "low"
            revenue_ratio = (daily_rev * days)
            if revenue_ratio > 0:
                debt_to_revenue = (daily_debt_service * days) / revenue_ratio
                if debt_to_revenue > 0.25:
                    pressure = "high"
                elif debt_to_revenue > 0.10:
                    pressure = "medium"

            forecast_periods[f"forecast_{days}d"] = ForecastPeriod(
                days=days,
                cash_in=round(cash_in, 2),
                cash_out=round(cash_out, 2),
                net_cash_flow=round(net_cash_flow, 2),
                ending_cash=round(ending_cash, 2),
                burn_rate=round(burn_rate, 2),
                liquidity_runway_days=round(runway, 1),
                ebitda=round(ebitda, 2),
                debt_servicing_pressure=pressure
            )

        # Generate smart financial warnings
        if ending_cash < 500_000:
            warnings.append(f"CRITICAL: Liquidity reserves fall below emergency thresholds ($500k) within {periods[-1]} days.")
        if any(p.debt_servicing_pressure == "high" for p in forecast_periods.values()):
            warnings.append("WARNING: High debt service pressure detected. Refinancing or interest variable restructuring is highly advised.")
        if adjusted_rev_annual < adjusted_exp_annual:
            warnings.append("STRUCTURAL DEFICIT: Base expenditures exceed baseline revenue. Immediate cost reduction required.")

        return ScenarioForecastResult(
            scenario=scenario_name,
            assumptions=assumptions,
            forecast_30d=forecast_periods["forecast_30d"],
            forecast_60d=forecast_periods["forecast_60d"],
            forecast_90d=forecast_periods["forecast_90d"],
            forecast_180d=forecast_periods["forecast_180d"],
            ebitda_trend=[round(x, 2) for x in ebitda_trend],
            warnings=warnings
        )
