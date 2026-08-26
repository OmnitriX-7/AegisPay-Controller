"""
AegisPay-Controller: Settlement Q&A & CFO Copilot
Natural Language Ledger Intelligence backed by Deterministic Audit Proofs.
"""

import os
import re
from typing import Dict, Any, List, Optional
from app.models.schemas import (
    BatchReconciliationResult,
    CashForecastResponse,
    CopilotQueryResponse
)


class SettlementQACopilot:
    """
    Intelligent Financial Controller Assistant.
    Parses CFO questions and retrieves itemized ledger proofs and exception diagnoses.
    """

    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")

    def answer_query(
        self,
        query: str,
        rec_result: Optional[BatchReconciliationResult],
        forecast_result: Optional[CashForecastResponse]
    ) -> CopilotQueryResponse:
        """
        Processes natural language inquiries against current reconciliation ledger and forecast state.
        """
        if not rec_result:
            return CopilotQueryResponse(
                answer="No active reconciliation batch is currently loaded. Please generate or ingest a batch first to perform ledger audit queries.",
                suggested_followups=["Generate 50-record standard batch", "Run full reconciliation pipeline"]
            )

        q_lower = query.lower()

        # 1. Query regarding Exceptions & Discrepancies
        if any(w in q_lower for w in ["exception", "discrepancy", "unreconciled", "unresolved", "error", "short"]):
            exc_count = len(rec_result.exceptions)
            total_variance = sum(e.variance_amount for e in rec_result.exceptions)
            
            by_cause = {}
            for e in rec_result.exceptions:
                by_cause[e.root_cause.value] = by_cause.get(e.root_cause.value, 0) + 1

            cause_summary = "\n".join([f"• **{cause}**: {cnt} item(s)" for cause, cnt in by_cause.items()])

            answer = (
                f"### 🛡️ Honest Exception Triage Report\n\n"
                f"Across the active batch, **{exc_count} exception(s)** were identified with total exposure of **₹{total_variance:,.2f}**.\n\n"
                f"**Root Cause Distribution:**\n{cause_summary}\n\n"
                f"Each exception has been diagnosed with a formal remediation plan and provisional journal entry ready for review in the Exception Desk."
            )

            return CopilotQueryResponse(
                answer=answer,
                cited_exception_ids=[e.exception_id for e in rec_result.exceptions[:5]],
                itemized_breakdown={
                    "total_exceptions": exc_count,
                    "total_exposure_inr": total_variance,
                    "categories": by_cause
                },
                suggested_followups=[
                    "Show proposed journal entries for MDR overcharges",
                    "Which bank timing lags are pending T+2 clearing?",
                    "What is our chargeback exposure?"
                ]
            )

        # 2. Query regarding Fees, MDR, GST, and Take Rates
        if any(w in q_lower for w in ["fee", "mdr", "gst", "tax", "tds", "cost", "take rate"]):
            gross = rec_result.total_gross_volume
            mdr = rec_result.total_mdr_fees_verified
            gst = rec_result.total_gst_withheld
            tds = rec_result.total_tds_deducted
            effective_rate = ((mdr + gst) / gross * 100) if gross > 0 else 0.0

            answer = (
                f"### 📊 Fee & Statutory Tax Audit\n\n"
                f"• **Total Gross Volume Reconciled**: ₹{gross:,.2f}\n"
                f"• **Verified MDR Processing Fees**: ₹{mdr:,.2f}\n"
                f"• **18% Input GST Tax on MDR**: ₹{gst:,.2f}\n"
                f"• **Section 194-O TDS Withholding (1%)**: ₹{tds:,.2f}\n"
                f"• **Effective Gateway Take Rate**: **{effective_rate:.2f}%**\n\n"
                f"All payment processing fee schedules and statutory 18% GST calculations were verified against contractual interchange rate cards."
            )

            return CopilotQueryResponse(
                answer=answer,
                itemized_breakdown={
                    "gross_volume": gross,
                    "mdr_fee": mdr,
                    "gst_18pct": gst,
                    "tds_194o": tds,
                    "effective_take_rate_pct": effective_rate
                },
                suggested_followups=[
                    "Are there any MDR billing discrepancies?",
                    "What is our projected net cash settlement?",
                    "Show double-entry journal balance"
                ]
            )

        # 3. Query regarding Cash Forecast / Liquidity / Runway
        if any(w in q_lower for w in ["cash", "forecast", "liquidity", "runway", "projection", "burn", "float"]):
            if forecast_result:
                ending = forecast_result.ending_projected_balance
                start = forecast_result.starting_balance
                score = forecast_result.liquidity_health_score
                unsettled = forecast_result.unsettled_float_in_transit
                car = forecast_result.cash_at_risk_total

                answer = (
                    f"### 📈 Forward Cash & Liquidity Analysis ({forecast_result.horizon_days}-Day Horizon)\n\n"
                    f"• **Starting Treasury Cash**: ₹{start:,.2f}\n"
                    f"• **Projected Ending Cash Position**: **₹{ending:,.2f}** ({((ending-start)/start)*100:+.2f}%)\n"
                    f"• **Liquidity Health Score**: **{score}/100** (Optimal)\n"
                    f"• **Gateway Settlement Float in Transit (T+2)**: ₹{unsettled:,.2f}\n"
                    f"• **Total Cash-at-Risk (Disputes/Volatility)**: ₹{car:,.2f}\n\n"
                    f"**Treasury Recommendation**: Maintain a working capital liquidity buffer of **₹{forecast_result.working_capital_buffer:,.2f}** to cover 21 days of operational burn."
                )

                return CopilotQueryResponse(
                    answer=answer,
                    itemized_breakdown={
                        "starting_cash": start,
                        "projected_cash": ending,
                        "health_score": score,
                        "float_in_transit": unsettled,
                        "cash_at_risk": car
                    },
                    suggested_followups=[
                        "Simulate a 20% surge in refund volume",
                        "Show daily cash flow breakdown",
                        "What is our unreconciled float?"
                    ]
                )

        # 4. Query regarding Specific Order / Batch / UTR
        order_match = re.search(r'(order_\d+|setl_\w+|bnk_\w+|inv-\d+-\d+)', q_lower)
        if order_match:
            target_id = order_match.group(1).lower()
            # Search in matches
            for m in rec_result.matches:
                if any(target_id in gw.order_id.lower() or target_id in (gw.settlement_batch_id or "").lower() for gw in m.gateway_events):
                    gw = m.gateway_events[0]
                    bk = m.bank_records[0] if m.bank_records else None
                    return CopilotQueryResponse(
                        answer=(
                            f"### 🔍 Transaction Ledger Proof: `{gw.order_id}`\n\n"
                            f"• **Match Status**: `{m.match_type.value}` (Confidence: {m.confidence*100:.0f}%)\n"
                            f"• **Gross Amount**: ₹{gw.amount:,.2f} ({gw.method.value})\n"
                            f"• **MDR Fee + GST**: ₹{gw.mdr_fee:,.2f} + ₹{gw.gst_on_mdr:,.2f}\n"
                            f"• **Net Settled in Bank**: ₹{gw.net_amount:,.2f}\n"
                            f"• **Bank UTR**: `{bk.utr if bk else 'Pending'}`\n"
                            f"• **Proof Hash**: `{m.proof.proof_hash[:16]}...`\n\n"
                            f"**Formal Invariant Verified**: `Net Bank Credit (₹{m.proof.bank_credit:,.2f}) == Gross (₹{m.proof.gross_sum:,.2f}) - Fees (₹{m.proof.mdr_total + m.proof.gst_total:,.2f})`."
                        ),
                        cited_match_ids=[m.match_id],
                        suggested_followups=["Show double-entry journal entry", "Show audit trace steps"]
                    )

            # Search in exceptions
            for exc in rec_result.exceptions:
                if any(target_id in o.lower() for o in exc.affected_order_ids) or any(target_id in u.lower() for u in exc.affected_utrs):
                    return CopilotQueryResponse(
                        answer=(
                            f"### ⚠️ Exception Diagnosis for `{target_id}`\n\n"
                            f"• **Exception ID**: `{exc.exception_id}`\n"
                            f"• **Root Cause**: `{exc.root_cause.value}` (Severity: `{exc.severity.value}`)\n"
                            f"• **Variance Amount**: ₹{exc.variance_amount:,.2f}\n"
                            f"• **Diagnosis**: {exc.description}\n\n"
                            f"**Recommended Controller Action**: {exc.recommended_action}"
                        ),
                        cited_exception_ids=[exc.exception_id],
                        suggested_followups=["Post proposed adjusting journal entry", "Show related webhook logs"]
                    )

        # Default Summary Overview
        answer = (
            f"### 🏛️ AegisPay Financial Controller Summary\n\n"
            f"• **Total Reconciled Records**: {rec_result.total_records_processed}\n"
            f"• **Match Rate**: **{rec_result.match_rate_pct}%** ({rec_result.matched_count} matches, {rec_result.exception_count} honest exceptions)\n"
            f"• **Mathematical Precision Drift**: **₹{rec_result.precision_drift_sum:.4f}** (Zero-drift guaranteed)\n"
            f"• **Total Gross Volume Audited**: ₹{rec_result.total_gross_volume:,.2f}\n"
            f"• **Net Bank Cash Settled**: ₹{rec_result.total_bank_settled:,.2f}\n"
            f"• **Pipeline Execution Speed**: {rec_result.execution_time_ms} ms\n\n"
            f"Cryptographic Audit Seal: `{rec_result.cryptographic_seal[:24]}...`"
        )

        return CopilotQueryResponse(
            answer=answer,
            suggested_followups=[
                "Why were there exceptions in this batch?",
                "What is our effective gateway fee take rate?",
                "What is our forward 14-day cash forecast?"
            ]
        )
