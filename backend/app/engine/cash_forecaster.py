"""
AegisPay-Controller: Forward Cash & Liquidity Forecaster
Predicts multi-day settlement liquidity, rolling reserves, and cash-at-risk using Monte Carlo simulations.
Includes what-if treasury stress simulation with parameter multipliers.
"""

import math
import random
from datetime import datetime, timedelta
from typing import List
import numpy as np

from app.models.schemas import (
    CashForecastPoint,
    CashForecastResponse,
    BatchReconciliationResult
)


class ForwardCashForecaster:
    """
    Simulates treasury cash position, float in transit,
    expected settlement rollovers, and working capital buffers.
    Supports What-If stress testing for CFO scenario planning.
    """

    def __init__(self, seed: int = 1337):
        self.rng = random.Random(seed)
        np.random.seed(seed)

    def forecast_cash_position(
        self,
        reconciliation_result: BatchReconciliationResult,
        starting_cash: float = 12500000.0, # ₹1.25 Cr default treasury cash
        horizon_days: int = 14,
        daily_operational_burn: float = 180000.0, # ₹1.8L daily burn
        sales_growth_pct: float = 0.0, # e.g. +10% or -15%
        refund_spike_pct: float = 3.0, # baseline 3%, spike up to 15%
        clearing_lag_days: int = 2 # T+1, T+2, T+3 bank clearing
    ) -> CashForecastResponse:
        """
        Runs Monte Carlo forward trajectory simulation for liquidity management.
        Applies stress scenario multipliers.
        """
        projections: List[CashForecastPoint] = []
        base_date = datetime.now()

        # Extract unreconciled float & expected incoming settlements
        unsettled_float = sum(
            exc.variance_amount for exc in reconciliation_result.exceptions
            if exc.root_cause.value == "BANK_TIMING_LAG_T_PLUS_N"
        )
        if unsettled_float == 0:
            unsettled_float = reconciliation_result.total_gross_volume * 0.15

        current_cash = starting_cash
        simulated_paths = 500  # Monte Carlo paths

        # Base daily transaction inflow volume estimate with sales growth stress modifier
        growth_multiplier = 1.0 + (sales_growth_pct / 100.0)
        daily_inflow_mean = max(450000.0, (reconciliation_result.total_gross_volume / 7.0)) * growth_multiplier
        daily_inflow_std = daily_inflow_mean * 0.18

        total_cash_at_risk = 0.0
        reserve_rate = max(0.02, min(0.20, refund_spike_pct / 100.0))

        for day in range(1, horizon_days + 1):
            cur_date = base_date + timedelta(days=day)
            date_str = cur_date.strftime("%Y-%m-%d")
            is_weekend = cur_date.weekday() >= 5

            # Clearing lag adjustment
            lag_factor = 1.0 / max(1, clearing_lag_days)
            settlement_multiplier = 0.20 if is_weekend else (1.4 * lag_factor if cur_date.weekday() == 0 else 1.0 * lag_factor)
            
            # Monte Carlo sampling for daily inflow
            inflows_mc = np.random.normal(daily_inflow_mean * settlement_multiplier, daily_inflow_std, simulated_paths)
            inflows_mc = np.clip(inflows_mc, 0, None)

            # Daily Operational Outflows / Vendor Payouts
            outflow_mean = daily_operational_burn * (0.3 if is_weekend else 1.0)
            outflows_mc = np.random.normal(outflow_mean, outflow_mean * 0.10, simulated_paths)

            # Reserve Holdback for Chargebacks & Refund Spikes
            reserve_holdback = float(np.mean(inflows_mc) * reserve_rate)

            # Expected Net Daily Cash Delta
            net_delta_mc = inflows_mc - outflows_mc - (inflows_mc * reserve_rate)

            expected_inflow = float(np.mean(inflows_mc))
            expected_outflow = float(np.mean(outflows_mc))
            
            # Update current cash
            current_cash += (expected_inflow - expected_outflow - reserve_holdback)

            # Compute 95% Confidence Interval
            lower_ci = current_cash - (float(np.std(net_delta_mc)) * 1.96 * math.sqrt(day))
            upper_ci = current_cash + (float(np.std(net_delta_mc)) * 1.96 * math.sqrt(day))

            # Cash-at-risk (Dispute & volatility exposure)
            daily_car = float(expected_inflow * (reserve_rate * 0.8))
            total_cash_at_risk += daily_car

            projections.append(CashForecastPoint(
                date=date_str,
                projected_cash_balance=round(current_cash, 2),
                lower_bound_95ci=round(lower_ci, 2),
                upper_bound_95ci=round(upper_ci, 2),
                expected_gateway_settlements=round(expected_inflow, 2),
                expected_payouts_and_burn=round(expected_outflow, 2),
                reserve_holdback=round(reserve_holdback, 2),
                cash_at_risk=round(daily_car, 2)
            ))

        ending_balance = projections[-1].projected_cash_balance
        liquidity_ratio = ending_balance / (daily_operational_burn * 30.0) if daily_operational_burn > 0 else 1.0
        liquidity_score = min(100.0, max(15.0, round(liquidity_ratio * 35.0, 1)))

        working_capital_buffer = daily_operational_burn * 21.0 # 21 days runway buffer

        scenario_tag = f"Growth: {sales_growth_pct:+.1f}%, Refund Spike: {refund_spike_pct:.1f}%, Clearing: T+{clearing_lag_days}"

        insights = [
            f"Scenario: {scenario_tag} | Projected {horizon_days}-day ending cash: ₹{ending_balance:,.2f} ({((ending_balance - starting_cash)/starting_cash)*100:+.2f}% net change).",
            f"Gateway float in-transit: ₹{unsettled_float:,.2f} scheduled across T+{clearing_lag_days} clearing cycles.",
            f"Cumulative Cash-at-Risk under {refund_spike_pct:.1f}% reserve buffer: ₹{total_cash_at_risk:,.2f}.",
            f"Recommended minimum liquidity reserve: ₹{working_capital_buffer:,.2f} (covers 21 days operational burn)."
        ]

        return CashForecastResponse(
            horizon_days=horizon_days,
            starting_balance=round(starting_cash, 2),
            ending_projected_balance=round(ending_balance, 2),
            liquidity_health_score=liquidity_score,
            burn_rate_daily_avg=round(daily_operational_burn, 2),
            unsettled_float_in_transit=round(unsettled_float, 2),
            working_capital_buffer=round(working_capital_buffer, 2),
            cash_at_risk_total=round(total_cash_at_risk, 2),
            projections=projections,
            liquidity_insights=insights
        )
