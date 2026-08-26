"""
AegisPay-Controller: Honest Exception Classifier & HITL Action Engine
Categorizes real fintech reconciliation exceptions without cherry-picking.
"""

import uuid
from typing import List, Dict, Any, Optional
from app.models.ledger_types import (
    ExceptionRootCause,
    ExceptionSeverity,
    ConfidenceLevel
)
from app.models.schemas import (
    GatewayEvent,
    BankStatementRecord,
    ERPInvoice,
    TaxRecord,
    ExceptionRecord
)


class HonestExceptionClassifier:
    """
    Diagnoses root causes for unmatched items, computes exposure amount,
    and produces structured remediation steps and journal entries for CFO approval.
    """

    def diagnose_mdr_discrepancy(
        self,
        gw: GatewayEvent,
        expected_fee: float,
        actual_fee: float,
        delta: float
    ) -> ExceptionRecord:
        return ExceptionRecord(
            exception_id=f"EXC-{uuid.uuid4().hex[:8].upper()}",
            root_cause=ExceptionRootCause.MDR_RATE_DISCREPANCY,
            severity=ExceptionSeverity.MEDIUM,
            variance_amount=abs(delta),
            affected_order_ids=[gw.order_id],
            affected_utrs=[],
            raw_evidence={
                "gateway_id": gw.id,
                "order_id": gw.order_id,
                "payment_method": gw.method,
                "billed_mdr_rate": gw.mdr_rate,
                "expected_fee": expected_fee,
                "actual_fee_billed": actual_fee,
                "overcharge_delta": delta
            },
            description=f"Gateway overcharged processing fees on order {gw.order_id} ({gw.method}). Billed ₹{actual_fee:.2f} vs contractual ₹{expected_fee:.2f} (Delta: ₹{delta:+.2f}).",
            recommended_action="Raise automated dispute ticket with Razorpay Merchant Operations for MDR billing adjustment and clawback credit note.",
            suggested_journal_entry={
                "debit": "1310 - Razorpay Fee Disputes Recoverable",
                "credit": "5020 - Payment Gateway Processing Expense",
                "amount": abs(delta)
            }
        )

    def diagnose_timing_lag(
        self,
        gw: GatewayEvent
    ) -> ExceptionRecord:
        return ExceptionRecord(
            exception_id=f"EXC-{uuid.uuid4().hex[:8].upper()}",
            root_cause=ExceptionRootCause.BANK_TIMING_LAG_T_PLUS_N,
            severity=ExceptionSeverity.LOW,
            variance_amount=gw.net_amount,
            affected_order_ids=[gw.order_id],
            affected_utrs=[],
            raw_evidence={
                "gateway_id": gw.id,
                "order_id": gw.order_id,
                "net_settlement_due": gw.net_amount,
                "capture_timestamp": gw.timestamp,
                "settlement_batch_id": gw.settlement_batch_id
            },
            description=f"Order {gw.order_id} (₹{gw.net_amount:,.2f}) captured in gateway on {gw.timestamp[:10]} is pending bank clearing (T+2 settlement cycle window).",
            recommended_action="Monitor next clearing cycle feed (T+2). Automatically reconcile when bank settlement batch arrives.",
            suggested_journal_entry={
                "debit": "1020 - Undeposited Gateway Settlement Float",
                "credit": "1200 - Accounts Receivable",
                "amount": gw.net_amount
            }
        )

    def diagnose_unmatched_clawback(
        self,
        bank: BankStatementRecord
    ) -> ExceptionRecord:
        return ExceptionRecord(
            exception_id=f"EXC-{uuid.uuid4().hex[:8].upper()}",
            root_cause=ExceptionRootCause.UNMATCHED_CHARGEBACK_CLAWBACK,
            severity=ExceptionSeverity.HIGH,
            variance_amount=bank.amount,
            affected_order_ids=[],
            affected_utrs=[bank.utr],
            raw_evidence={
                "bank_id": bank.id,
                "utr": bank.utr,
                "narration": bank.description,
                "debit_amount": bank.amount,
                "date": bank.date
            },
            description=f"Direct bank debit of ₹{bank.amount:,.2f} on {bank.date} (UTR: {bank.utr}) detected with narration '{bank.description}' without corresponding ERP dispute ticket.",
            recommended_action="Cross-reference bank chargeback reference with customer support dispute portal. Post provisional dispute loss provision.",
            suggested_journal_entry={
                "debit": "5080 - Chargeback Loss / Dispute Provision",
                "credit": "1010 - Bank Account",
                "amount": bank.amount
            }
        )

    def diagnose_tds_withholding_gap(
        self,
        gw: GatewayEvent,
        erp: ERPInvoice,
        expected_tds: float
    ) -> ExceptionRecord:
        return ExceptionRecord(
            exception_id=f"EXC-{uuid.uuid4().hex[:8].upper()}",
            root_cause=ExceptionRootCause.GST_TDS_WITHHOLDING_GAP,
            severity=ExceptionSeverity.MEDIUM,
            variance_amount=expected_tds,
            affected_order_ids=[gw.order_id],
            affected_utrs=[],
            raw_evidence={
                "order_id": gw.order_id,
                "invoice_id": erp.invoice_id,
                "gross_invoice": erp.gross_amount,
                "gateway_settled_net": gw.net_amount,
                "tds_deducted_under_194o": expected_tds
            },
            description=f"Statutory 1% TDS under Section 194-O (₹{expected_tds:.2f}) was deducted by gateway on order {gw.order_id}, but merchant ERP booked gross without tax withholding.",
            recommended_action="Post adjusting subledger entry to claim TDS credit against GSTR / Income Tax Form 26AS.",
            suggested_journal_entry={
                "debit": "1430 - Section 194-O Prepaid TDS Asset",
                "credit": "1200 - Accounts Receivable",
                "amount": expected_tds
            }
        )

    def diagnose_duplicate_webhook(
        self,
        duplicate_events: List[GatewayEvent]
    ) -> ExceptionRecord:
        order_id = duplicate_events[0].order_id
        gross = duplicate_events[0].amount
        return ExceptionRecord(
            exception_id=f"EXC-{uuid.uuid4().hex[:8].upper()}",
            root_cause=ExceptionRootCause.DUPLICATE_GATEWAY_WEBHOOK,
            severity=ExceptionSeverity.LOW,
            variance_amount=gross,
            affected_order_ids=[order_id],
            affected_utrs=[],
            raw_evidence={
                "duplicate_count": len(duplicate_events),
                "gateway_event_ids": [g.id for g in duplicate_events],
                "order_id": order_id
            },
            description=f"Duplicate payment.captured webhook events ({len(duplicate_events)}x) detected for order {order_id}. Bank ledger confirms single settlement.",
            recommended_action="De-duplicate webhook payload in idempotent event log. Retain primary event ID and discard duplicate replay.",
            suggested_journal_entry=None
        )

    def diagnose_unclaimed_credit(
        self,
        bank: BankStatementRecord
    ) -> ExceptionRecord:
        return ExceptionRecord(
            exception_id=f"EXC-{uuid.uuid4().hex[:8].upper()}",
            root_cause=ExceptionRootCause.UNCLAIMED_BANK_CREDIT,
            severity=ExceptionSeverity.HIGH,
            variance_amount=bank.amount,
            affected_order_ids=[],
            affected_utrs=[bank.utr],
            raw_evidence={
                "bank_id": bank.id,
                "utr": bank.utr,
                "narration": bank.description,
                "amount": bank.amount,
                "date": bank.date
            },
            description=f"Unidentified bank deposit of ₹{bank.amount:,.2f} received on {bank.date} (UTR: {bank.utr}) with no matching order or gateway batch ID.",
            recommended_action="Place funds in 2190 - Suspense Clearing Account. Initiate customer remitter inquiry.",
            suggested_journal_entry={
                "debit": "1010 - Bank Account",
                "credit": "2190 - Unclaimed Customer Suspense Liability",
                "amount": bank.amount
            }
        )
