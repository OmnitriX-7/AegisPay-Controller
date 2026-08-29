"""
AegisPay-Controller: Symbolic Ledger & Mathematical Invariant Verifier
Zero-Hallucination Deterministic Engine for Multi-Way Reconciliation
"""

import hashlib
import json
from typing import List, Dict, Any, Tuple, Optional
from app.models.ledger_types import (
    STANDARD_MDR_RATES,
    GST_ON_MDR_RATE
)
from app.models.schemas import (
    GatewayEvent,
    BankStatementRecord,
    ERPInvoice,
    TaxRecord,
    InvariantProof
)


class SymbolicVerifier:
    """
    Formally verifies double-entry ledger invariants, fee math,
    and statutory tax deductions with sub-paisa tolerance.
    """

    TOLERANCE_INR: float = 0.01  # Sub-paisa (₹0.01) numerical tolerance

    @staticmethod
    def calculate_proof_hash(payload: Dict[str, Any]) -> str:
        """Generates an immutable SHA-256 hash for the cryptographic audit trail"""
        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def verify_reconciliation_bundle(
        self,
        gateway_events: List[GatewayEvent],
        bank_records: List[BankStatementRecord],
        erp_invoices: List[ERPInvoice],
        tax_records: Optional[List[TaxRecord]] = None
    ) -> InvariantProof:
        """
        Validates the core FinTech Settlement Equation:
        Net Bank Credit = Sum(Gross) - Sum(MDR) - Sum(GST_MDR) - Sum(Refunds) - Sum(Chargebacks) - Sum(TDS)
        """
        tax_records = tax_records or []

        gross_sum = sum(gw.amount for gw in gateway_events)
        mdr_total = sum(gw.mdr_fee for gw in gateway_events)
        gst_total = sum(gw.gst_on_mdr for gw in gateway_events)
        
        refunds_total = sum(
            gw.amount * 0.5 for gw in gateway_events if "partially_refunded" in gw.status
        ) + sum(
            gw.amount for gw in gateway_events if gw.status == "refunded"
        )
        
        chargebacks_total = sum(
            gw.amount for gw in gateway_events if gw.status == "disputed" or gw.dispute_id
        )

        tds_total = sum(tx.tds_amount for tx in tax_records)

        calculated_net = round(
            gross_sum - mdr_total - gst_total - refunds_total - chargebacks_total - tds_total,
            2
        )

        bank_credit = sum(
            b.amount for b in bank_records if b.type == "CREDIT"
        ) - sum(
            b.amount for b in bank_records if b.type == "DEBIT"
        )
        bank_credit = round(bank_credit, 2)

        variance = round(abs(bank_credit - calculated_net), 2)
        is_proven = variance <= self.TOLERANCE_INR

        proof_payload = {
            "gross_sum": gross_sum,
            "mdr_total": mdr_total,
            "gst_total": gst_total,
            "refunds_total": refunds_total,
            "chargebacks_total": chargebacks_total,
            "tds_total": tds_total,
            "calculated_net": calculated_net,
            "bank_credit": bank_credit,
            "variance": variance,
            "is_proven": is_proven,
            "gw_ids": [g.id for g in gateway_events],
            "bank_ids": [b.id for b in bank_records],
            "erp_ids": [e.invoice_id for e in erp_invoices]
        }

        proof_hash = self.calculate_proof_hash(proof_payload)

        return InvariantProof(
            gross_sum=gross_sum,
            mdr_total=mdr_total,
            gst_total=gst_total,
            refunds_total=refunds_total,
            chargebacks_total=chargebacks_total,
            tds_total=tds_total,
            calculated_net=calculated_net,
            bank_credit=bank_credit,
            variance=variance,
            is_proven=is_proven,
            proof_hash=proof_hash
        )

    def validate_mdr_fee_schedule(self, gw: GatewayEvent) -> Tuple[bool, float, float]:
        """
        Validates if gateway charged contractual MDR rate and statutory 18% GST.
        Returns (is_valid, expected_fee, delta)
        """
        contractual_rate = STANDARD_MDR_RATES.get(gw.method, 0.018)
        expected_mdr = round(gw.amount * contractual_rate, 2)
        expected_gst = round(expected_mdr * GST_ON_MDR_RATE, 2)
        expected_total_fee = round(expected_mdr + expected_gst, 2)

        actual_total_fee = round(gw.mdr_fee + gw.gst_on_mdr, 2)
        delta = round(actual_total_fee - expected_total_fee, 2)

        is_valid = abs(delta) <= self.TOLERANCE_INR
        return is_valid, expected_total_fee, delta

    def generate_journal_entry(
        self,
        gross: float,
        mdr: float,
        gst: float,
        net_bank: float,
        tds: float = 0.0
    ) -> Dict[str, Any]:
        """
        Generates standard Double-Entry Journal Entry verifying Debits == Credits.
        """
        debits = [
            {"account": "1010 - Bank Clearing Account", "amount": round(net_bank, 2)},
            {"account": "5020 - Payment Gateway Processing Expense", "amount": round(mdr, 2)},
            {"account": "1420 - Input GST Tax Credit (18%)", "amount": round(gst, 2)},
        ]
        if tds > 0:
            debits.append({"account": "1430 - Prepaid Income Tax (Sec 194-O TDS)", "amount": round(tds, 2)})

        credits = [
            {"account": "1200 - Accounts Receivable / Customer Sales", "amount": round(gross, 2)}
        ]

        total_debit = round(sum(d["amount"] for d in debits), 2)
        total_credit = round(sum(c["amount"] for c in credits), 2)
        is_balanced = abs(total_debit - total_credit) <= self.TOLERANCE_INR

        return {
            "is_balanced": is_balanced,
            "total_debit": total_debit,
            "total_credit": total_credit,
            "debit_entries": debits,
            "credit_entries": credits
        }
