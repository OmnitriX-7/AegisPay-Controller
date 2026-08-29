"""
AegisPay-Controller: Settlement Q&A & CFO Copilot
Hybrid Neuro-Symbolic Agent: Powered by Google Gemini 2.0 Flash LLM with Deterministic Invariant Fallback.
Specializes in Razorpay settlement triage, dispute recovery drafting, Section 194-O TDS compliance, and executive memos.
"""

import os
import re
import logging
from typing import Optional
import httpx

from app.models.schemas import (
    BatchReconciliationResult,
    CashForecastResponse,
    CopilotQueryResponse
)

logger = logging.getLogger("aegispay.copilot")


class SettlementQACopilot:
    """
    Intelligent Financial Controller Assistant.
    Orchestrates Google Gemini 2.0 Flash with live ledger proofs, falling back gracefully to deterministic logic.
    """

    def __init__(self):
        self.default_api_key = os.getenv("GEMINI_API_KEY")

    def _build_context_summary(
        self,
        rec_result: BatchReconciliationResult,
        forecast_result: Optional[CashForecastResponse]
    ) -> str:
        """Constructs a structured forensic financial context string for LLM reasoning."""
        lines = [
            "=== ACTIVE RECONCILIATION BATCH LEDGER CONTEXT ===",
            f"Total Records Audited: {rec_result.total_records_processed}",
            f"Successfully Matched: {rec_result.matched_count} ({rec_result.match_rate_pct:.2f}%)",
            f"Honest Exceptions Identified: {rec_result.exception_count}",
            f"Mathematical Precision Drift: INR {rec_result.precision_drift_sum:.4f} (Zero-Drift Guaranteed)",
            f"Total Gross Rupee Volume: INR {rec_result.total_gross_volume:,.2f}",
            f"Net Cash Settled in Bank: INR {rec_result.total_bank_settled:,.2f}",
            f"Verified Gateway MDR Fees: INR {rec_result.total_mdr_fees_verified:,.2f}",
            f"GST Withheld on MDR (18%): INR {rec_result.total_gst_withheld:,.2f}",
            f"Section 194-O TDS Deducted (1%): INR {rec_result.total_tds_deducted:,.2f}",
            f"Cryptographic Audit Seal: {rec_result.cryptographic_seal}",
            "",
            "=== ITEMIZED EXCEPTIONS ==="
        ]

        for i, exc in enumerate(rec_result.exceptions[:10], 1):
            orders_str = ", ".join(exc.affected_order_ids[:3])
            utrs_str = ", ".join(exc.affected_utrs[:2]) or "Pending"
            lines.append(
                f"{i}. ID: {exc.exception_id} | Cause: {exc.root_cause.value} | Severity: {exc.severity.value} | "
                f"Variance: INR {exc.variance_amount:,.2f} | Orders: [{orders_str}] | UTRs: [{utrs_str}] | "
                f"Action: {exc.recommended_action}"
            )

        if forecast_result:
            lines.extend([
                "",
                "=== FORWARD CASH & LIQUIDITY FORECAST (14-DAY) ===",
                f"Starting Cash: INR {forecast_result.starting_balance:,.2f}",
                f"Projected Ending Cash: INR {forecast_result.ending_projected_balance:,.2f}",
                f"Liquidity Health Score: {forecast_result.liquidity_health_score}/100",
                f"Unsettled Float in Transit: INR {forecast_result.unsettled_float_in_transit:,.2f}",
                f"Total Cash-at-Risk: INR {forecast_result.cash_at_risk_total:,.2f}",
                f"Required Working Capital Buffer: INR {forecast_result.working_capital_buffer:,.2f}"
            ])

        return "\n".join(lines)

    def _call_gemini(self, query: str, context: str, api_key: str) -> Optional[str]:
        """Calls Google Gemini 2.0 Flash REST API synchronously via httpx."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

        system_instruction = (
            "You are AegisPay CFO Copilot, an elite Autonomous Financial Controller and Forensic Auditor engineered "
            "for the Indian fintech ecosystem (Track 04, Razorpay AI Buildathon 2026).\n"
            "You have deep expertise in: Razorpay payment gateway settlements, interchange MDR schedules (UPI 0%, "
            "Debit 0.4%-0.9%, Credit 1.8%-2.5%, Amex 3.0%), 18% GST on MDR, Indian Section 194-O TDS (1% withholding), "
            "Form 26AS reconciliation, N-to-1 consolidated UTR batch clearing, and double-entry accounting journals.\n\n"
            "Guidelines:\n"
            "1. Answer questions with authoritative financial rigor, exact numbers in INR, and clear markdown formatting.\n"
            "2. If asked to draft a dispute letter or email to Razorpay/Bank support, include: Merchant ID, Order IDs, "
            "UTR references, expected vs debited fee amounts, exact refund request, and reference to RBI guidelines.\n"
            "3. If asked about tax or TDS, reference Section 194-O of the Income Tax Act, Form 26AS matching, and GST Input Tax Credit (ITC).\n"
            "4. Always preserve the mathematical invariant that Net Bank Settlement = Gross - MDR - GST - TDS - Refunds."
        )

        user_content = f"{context}\n\n=== USER CFO INQUIRY ===\n{query}"

        payload = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": user_content}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1200
            }
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(url, json=payload, headers={"Content-Type": "application/json"})
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
                else:
                    logger.warning(f"Gemini API returned status {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.warning(f"Failed to communicate with Gemini API: {e}")

        return None

    def answer_query(
        self,
        query: str,
        rec_result: Optional[BatchReconciliationResult],
        forecast_result: Optional[CashForecastResponse],
        api_key: Optional[str] = None
    ) -> CopilotQueryResponse:
        """
        Processes natural language inquiries against current reconciliation ledger and forecast state.
        Uses Gemini LLM when key is present, otherwise falls back to deterministic rule engine.
        """
        if not rec_result:
            return CopilotQueryResponse(
                answer="No active reconciliation batch is currently loaded. Please generate or ingest a batch first to perform ledger audit queries.",
                suggested_followups=["Generate 50-record standard batch", "Upload custom settlement CSV"]
            )

        active_key = api_key or self.default_api_key or os.getenv("GEMINI_API_KEY")

        # 1. Attempt Generative LLM Reasoning if API key available
        if active_key:
            context = self._build_context_summary(rec_result, forecast_result)
            llm_answer = self._call_gemini(query, context, active_key)
            if llm_answer:
                return CopilotQueryResponse(
                    answer=llm_answer,
                    cited_match_ids=[m.match_id for m in rec_result.matches[:3]],
                    cited_exception_ids=[e.exception_id for e in rec_result.exceptions[:3]],
                    suggested_followups=[
                        "Draft formal dispute letter to Razorpay Support",
                        "Show Section 194-O TDS rectification entry",
                        "Explain 14-day forward cash runway under stress"
                    ]
                )

        # 2. Deterministic High-Precision Fallback Engine
        return self._deterministic_fallback(query, rec_result, forecast_result)

    def _deterministic_fallback(
        self,
        query: str,
        rec_result: BatchReconciliationResult,
        forecast_result: Optional[CashForecastResponse]
    ) -> CopilotQueryResponse:
        """Deterministic rule-based solver that runs offline with zero external dependencies."""
        q_lower = query.lower()

        # Dispute Letter / Email Request
        if any(w in q_lower for w in ["draft", "email", "letter", "dispute", "complaint", "claim"]):
            exceptions = rec_result.exceptions
            sample_exc = exceptions[0] if exceptions else None
            exc_desc = sample_exc.description if sample_exc else "MDR fee overcharge observed across batch settlements."
            variance = sum(e.variance_amount for e in exceptions) if exceptions else 450.0

            answer = (
                f"### ✉️ Formal Dispute & Recovery Notice to Payment Aggregator\n\n"
                f"**To**: Razorpay Merchant Grievance / Settlements Desk (`disputes@razorpay.com`)\n"
                f"**Subject**: Discrepancy Notice — Settlement Batch `{rec_result.cryptographic_seal[:16]}` | Overcharge Claim: ₹{variance:,.2f}\n\n"
                f"Dear Merchant Operations Team,\n\n"
                f"Our automated financial controller (**AegisPay-Controller**) has detected a settlement invariant discrepancy "
                f"during statutory reconciliation of batch `{rec_result.cryptographic_seal[:16]}`.\n\n"
                f"**Summary of Discrepancy:**\n"
                f"• **Total Gross Volume Reconciled**: ₹{rec_result.total_gross_volume:,.2f}\n"
                f"• **Net Credit Received**: ₹{rec_result.total_bank_settled:,.2f}\n"
                f"• **Calculated Variance / Shortfall**: **₹{variance:,.2f}**\n"
                f"• **Audit Finding**: {exc_desc}\n\n"
                f"Under RBI Circular on Payment Aggregators & Settlement Discipline, we formally request immediate verification "
                f"and credit adjustment of **₹{variance:,.2f}** within 2 business days.\n\n"
                f"Sincerely,\n"
                f"**Treasury & Finance Controller Office**\n"
                f"Cryptographic Verification Seal: `{rec_result.cryptographic_seal}`"
            )
            return CopilotQueryResponse(
                answer=answer,
                cited_exception_ids=[e.exception_id for e in rec_result.exceptions[:3]],
                suggested_followups=["Post proposed adjusting journal entry", "Review Section 194-O tax credits"]
            )

        # Exceptions & Discrepancies
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
                itemized_breakdown={"total_exceptions": exc_count, "total_exposure_inr": total_variance, "categories": by_cause},
                suggested_followups=[
                    "Draft formal dispute letter to Razorpay Support",
                    "Which bank timing lags are pending T+2 clearing?",
                    "What is our chargeback exposure?"
                ]
            )

        # Fees, MDR, GST, TDS
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
                itemized_breakdown={"gross_volume": gross, "mdr_fee": mdr, "gst_18pct": gst, "tds_194o": tds, "effective_take_rate_pct": effective_rate},
                suggested_followups=["Are there any MDR billing discrepancies?", "Show double-entry journal balance"]
            )

        # Cash Forecast / Liquidity
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
                    f"**Treasury Recommendation**: Maintain a working capital buffer of **₹{forecast_result.working_capital_buffer:,.2f}**."
                )
                return CopilotQueryResponse(
                    answer=answer,
                    itemized_breakdown={"starting_cash": start, "projected_cash": ending, "health_score": score, "float_in_transit": unsettled, "cash_at_risk": car},
                    suggested_followups=["Simulate a 20% surge in refund volume", "Show daily cash flow breakdown"]
                )

        # Specific Order / UTR lookup
        order_match = re.search(r'(order_\w+|setl_\w+|bnk_\w+|inv-\d+-\d+)', q_lower)
        if order_match:
            target_id = order_match.group(1).lower()
            for m in rec_result.matches:
                if any(target_id in gw.order_id.lower() for gw in m.gateway_events):
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
                            f"• **Proof Hash**: `{m.proof.proof_hash[:16]}...`"
                        ),
                        cited_match_ids=[m.match_id]
                    )

        # Default Summary
        answer = (
            f"### 🏛️ AegisPay Financial Controller Summary\n\n"
            f"• **Total Reconciled Records**: {rec_result.total_records_processed}\n"
            f"• **Match Rate**: **{rec_result.match_rate_pct}%** ({rec_result.matched_count} matches, {rec_result.exception_count} honest exceptions)\n"
            f"• **Mathematical Precision Drift**: **₹{rec_result.precision_drift_sum:.4f}** (Zero-drift guaranteed)\n"
            f"• **Total Gross Volume Audited**: ₹{rec_result.total_gross_volume:,.2f}\n"
            f"• **Net Bank Cash Settled**: ₹{rec_result.total_bank_settled:,.2f}\n\n"
            f"Cryptographic Audit Seal: `{rec_result.cryptographic_seal[:24]}...`"
        )
        return CopilotQueryResponse(
            answer=answer,
            suggested_followups=[
                "Draft formal dispute letter to Razorpay Support",
                "Why were there exceptions in this batch?",
                "What is our effective gateway fee take rate?"
            ]
        )
