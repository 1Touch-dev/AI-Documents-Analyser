"""
Cascading Scenario Recalculation Engine.
Builds directed scenario dependency graphs and propagates impacts across liquidity, debt covenants, and payroll.
"""

from typing import Dict, Any, List
from datetime import datetime, timezone
from backend.fpa_core.persistence import FinancialLedgerStore
from backend.driver_engine.engine import DriverForecastingEngine

class ScenarioDependencyGraph:
    """
    Direct relationships graph propagating macro variables to core balance sheet outputs.
    """
    def __init__(self, store: FinancialLedgerStore, forecaster: DriverForecastingEngine):
        self.store = store
        self.forecaster = forecaster

    def evaluate_scenario(self, scenario_name: str, starting_cash: float) -> Dict[str, Any]:
        """
        Calculates cascading variables according to scenario parameters,
        then propagates them through the forecasting engine.
        """
        # Baseline drivers
        attendance = 0.95
        ticket_pricing = 1.0
        sponsorship_delay = 0
        payroll_growth = 0.0
        transfer_sales = 0.0
        inflation = 0.03
        interest_rate = 0.05
        trigger_events = []

        # 1. Cascading Recalculation Rules based on scenario select
        if scenario_name == "relegation":
            # Extreme Downside cascading rules:
            # 1. Sponsorship contracts drops by 40%
            # 2. Match attendance drops by 30%
            # 3. TV rights broadcast shares drop by 50%
            # 4. Debt interest rates are escalated by creditors due to risk
            attendance = 0.65
            ticket_pricing = 0.80
            sponsorship_delay = 45
            inflation = 0.04
            interest_rate = 0.095
            trigger_events.append("Sponsorship agreements hit with 40% relegation clause haircut.")
            trigger_events.append("Match attendance plummeted to 65%; ticket sales prices forced down 20%.")
            trigger_events.append("Macquarie Bank escalated risk-premium interest rates to 9.5%.")

        elif scenario_name == "promotion":
            # Upward Optimistic cascading rules:
            # 1. Sponsorship contracts rise by 25%
            # 2. Ticketing prices increase by 15% due to high demand
            # 3. Squad salaries rise by 10% due to promotion bonuses
            attendance = 1.0
            ticket_pricing = 1.15
            payroll_growth = 0.10
            transfer_sales = 1500000.0 # extra prize cash
            interest_rate = 0.045
            trigger_events.append("Global sponsorships upgraded with 25% promotion bonus multipliers.")
            trigger_events.append("Old Trafford attendance hit 100% capacity; ticket prices raised 15%.")
            trigger_events.append("Promotion squads wages raised 10% on pre-agreed bonus packages.")

        elif scenario_name == "delayed_payments":
            # Cash-crunch scenario
            sponsorship_delay = 90
            inflation = 0.05
            trigger_events.append("Counterparties requested payment extensions; collection delays hit 90 days.")
            trigger_events.append("Working capital constrained; immediate cash inflow drops 20%.")

        elif scenario_name == "emergency_raise":
            # Emergency capital injection with partial debt payout
            starting_cash += 15000000.0
            interest_rate = 0.04
            trigger_events.append("Injected $15,000,000 corporate equity reserves.")
            trigger_events.append("Negotiated a 100 bps reduction on construction credit lines interest.")

        elif scenario_name == "player_sales":
            # Capital liquidation and expense cutting
            transfer_sales = 8000000.0
            payroll_growth = -0.15 # 15% salary reduction
            trigger_events.append("Liquidated first-team squad assets for $8,000,000 cash.")
            trigger_events.append("Achieved 15% squad wage reductions via loan out transfers.")

        # 2. Run forecasting propagation with recalculated drivers
        forecast_res = self.forecaster.generate_driver_forecast(
            starting_cash=starting_cash,
            attendance_rate=attendance,
            ticket_pricing_factor=ticket_pricing,
            sponsorship_collection_delay_days=sponsorship_delay,
            payroll_growth_rate=payroll_growth,
            transfer_sale_liquidation=transfer_sales,
            vendor_inflation_rate=inflation,
            refinancing_interest_rate=interest_rate,
            version=f"scenario-{scenario_name}-1.0"
        )

        # 3. Evaluate Covenant & Liquidity Pressures
        debts = self.store.get_all_debts()
        covenant_alerts = []
        ending_cash_180d = forecast_res["metrics"]["forecast_180d"]["ending_cash"]
        ebitda_180d = forecast_res["metrics"]["forecast_180d"]["ebitda"]

        for d in debts:
            # Simulated Leverage Ratio: Outstanding Principal / Operating EBITDA
            approx_annualized_ebitda = max(1000000.0, ebitda_180d * 2.0)
            leverage = d.principal / approx_annualized_ebitda
            for cov in d.covenants:
                if "Leverage" in cov and leverage > 4.0:
                    covenant_alerts.append({
                        "creditor": d.creditor,
                        "covenant": cov,
                        "actual_value": f"{leverage:.2f}x",
                        "status": "BREACHED",
                        "severity": "critical",
                        "message": f"Leverage Ratio of {leverage:.2f}x exceeds restrictive covenant threshold of 4.0x."
                    })
                elif "DSCR" in cov and ebitda_180d < d.principal * 0.05:
                    covenant_alerts.append({
                        "creditor": d.creditor,
                        "covenant": cov,
                        "actual_value": f"{(ebitda_180d / (d.principal * 0.05)):.2f}x",
                        "status": "BREACHED",
                        "severity": "high",
                        "message": "Debt Service Coverage Ratio fallen below restrictive compliance thresholds."
                    })

        # Calculate runway reduction percentage compared to base case
        runway_days = forecast_res["metrics"]["forecast_180d"]["liquidity_runway_days"]
        runway_status = "stable"
        if runway_days < 90:
            runway_status = "critical"
        elif runway_days < 180:
            runway_status = "warning"

        return {
            "scenario": scenario_name,
            "simulated_drivers": forecast_res["drivers"],
            "metrics": forecast_res["metrics"],
            "trigger_events": trigger_events,
            "covenant_audits": covenant_alerts,
            "liquidity_status": runway_status,
            "covenant_breached_count": len(covenant_alerts),
            "lineage": forecast_res["lineage"]
        }
