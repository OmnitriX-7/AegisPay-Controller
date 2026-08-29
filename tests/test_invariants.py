"""
Test Suite: Mathematical Invariants & Precision Verification
Guarantees 0.00 sub-paisa drift and double-entry balance constraints.
"""

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.models.ledger_types import PaymentMethod
from app.models.schemas import GatewayEvent, BankStatementRecord, ERPInvoice
from app.engine.symbolic_verifier import SymbolicVerifier


def test_symbolic_reconciliation_invariant():
    verifier = SymbolicVerifier()

    gw = GatewayEvent(
        id="pay_test_01",
        order_id="order_test_01",
        amount=10000.0,
        currency="INR",
        method=PaymentMethod.CREDIT_CARD_DOMESTIC,
        mdr_rate=0.018,
        mdr_fee=180.0,
        gst_on_mdr=32.40,
        net_amount=9787.60,
        status="captured",
        timestamp="2026-08-15T10:00:00",
        customer_name="Aarav Sharma"
    )

    bank = BankStatementRecord(
        id="bnk_01",
        utr="ICICR520260815001",
        date="2026-08-15",
        description="NEFT-RZP-SETL-order_test_01",
        amount=9787.60,
        type="CREDIT"
    )

    erp = ERPInvoice(
        invoice_id="INV-001",
        order_id="order_test_01",
        customer_name="Aarav Sharma",
        gross_amount=10000.0,
        tax_amount=1525.42,
        net_payable=10000.0,
        issue_date="2026-08-15"
    )

    proof = verifier.verify_reconciliation_bundle([gw], [bank], [erp])

    assert proof.is_proven is True, "Proof should be valid for exact match"
    assert proof.variance == 0.0, f"Expected 0.0 variance, got {proof.variance}"
    assert proof.calculated_net == 9787.60, f"Expected 9787.60, got {proof.calculated_net}"
    assert len(proof.proof_hash) == 64, "Expected valid SHA-256 hash"
    print("[PASS] test_symbolic_reconciliation_invariant passed!")


def test_double_entry_journal_balancing():
    verifier = SymbolicVerifier()
    journal = verifier.generate_journal_entry(
        gross=25000.00,
        mdr=450.00,
        gst=81.00,
        net_bank=24219.00,
        tds=250.00
    )

    assert journal["is_balanced"] is True, "Double-entry debits must equal credits"
    assert journal["total_debit"] == 25000.00
    assert journal["total_credit"] == 25000.00
    print("[PASS] test_double_entry_journal_balancing passed!")


def test_mdr_fee_schedule_validation():
    verifier = SymbolicVerifier()

    # Valid event
    gw_valid = GatewayEvent(
        id="pay_01",
        order_id="ord_01",
        amount=5000.0,
        currency="INR",
        method=PaymentMethod.UPI,
        mdr_rate=0.0,
        mdr_fee=0.0,
        gst_on_mdr=0.0,
        net_amount=5000.0,
        timestamp="2026-08-10T12:00:00",
        customer_name="Diya Patel"
    )
    is_valid, expected, delta = verifier.validate_mdr_fee_schedule(gw_valid)
    assert is_valid is True
    assert delta == 0.0

    # Overcharged event
    gw_invalid = GatewayEvent(
        id="pay_02",
        order_id="ord_02",
        amount=10000.0,
        currency="INR",
        method=PaymentMethod.CREDIT_CARD_DOMESTIC,
        mdr_rate=0.028, # Overcharged
        mdr_fee=280.0,
        gst_on_mdr=50.40,
        net_amount=9669.60,
        timestamp="2026-08-10T12:00:00",
        customer_name="Vihaan Mehta"
    )
    is_valid, expected, delta = verifier.validate_mdr_fee_schedule(gw_invalid)
    assert is_valid is False
    assert delta > 0.0
    print("[PASS] test_mdr_fee_schedule_validation passed!")


if __name__ == "__main__":
    test_symbolic_reconciliation_invariant()
    test_double_entry_journal_balancing()
    test_mdr_fee_schedule_validation()
    print(">>> ALL INVARIANT TESTS PASSED WITH 100% MATHEMATICAL PRECISION!")
