"""
Test Suite: End-to-End Multi-Source Reconciliation Pipeline
Tests realistic batches from 50 to 500 records.
"""

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.generator.synthetic_fintech import SyntheticFintechGenerator
from app.engine.neuro_symbolic_agent import NeuroSymbolicReconciler
from app.engine.cash_forecaster import ForwardCashForecaster
from app.copilot.settlement_qa import SettlementQACopilot
from app.models.schemas import GatewayEvent, BankStatementRecord, ERPInvoice, TaxRecord


def test_50_record_baseline_reconciliation():
    generator = SyntheticFintechGenerator(seed=42)
    reconciler = NeuroSymbolicReconciler()
    forecaster = ForwardCashForecaster()
    copilot = SettlementQACopilot()

    # 1. Generate 50-record dataset
    raw = generator.generate_batch(record_count=50)
    assert len(raw["gateway_events"]) >= 50, "Should generate at least 50 gateway records"

    gw_events = [GatewayEvent(**g) for g in raw["gateway_events"]]
    bank_recs = [BankStatementRecord(**b) for b in raw["bank_records"]]
    erp_invs = [ERPInvoice(**e) for e in raw["erp_invoices"]]
    tax_recs = [TaxRecord(**t) for t in raw["tax_records"]]

    # 2. Run Reconciliation Pipeline
    result = reconciler.reconcile_batch(gw_events, bank_recs, erp_invs, tax_recs)

    print("50-Record Batch Result:")
    print(f"  * Total Records Processed: {result.total_records_processed}")
    print(f"  * Matches Count: {result.matched_count}")
    print(f"  * Exceptions Count: {result.exception_count}")
    print(f"  * Match Rate: {result.match_rate_pct}%")
    print(f"  * Precision Drift: INR {result.precision_drift_sum:.4f}")
    print(f"  * Total Gross Volume: INR {result.total_gross_volume:,.2f}")
    print(f"  * Execution Time: {result.execution_time_ms} ms")

    assert result.match_rate_pct > 65.0, f"Match rate should exceed 65%, got {result.match_rate_pct}%"
    assert result.exception_count > 0, "Honest exceptions must be detected"
    assert result.precision_drift_sum == 0.0, "Precision drift must be strictly zero"
    assert result.cryptographic_seal is not None

    # 3. Test Cash Forecaster
    forecast = forecaster.forecast_cash_position(result, starting_cash=10000000.0, horizon_days=14)
    assert len(forecast.projections) == 14
    assert forecast.liquidity_health_score > 0
    print(f"  * 14-Day Forward Ending Cash: INR {forecast.ending_projected_balance:,.2f}")

    # 4. Test CFO Copilot Queries
    q1 = copilot.answer_query("Why are there exceptions in this batch?", result, forecast)
    assert len(q1.answer) > 20
    assert "Exception" in q1.answer

    q2 = copilot.answer_query("What is our forward cash forecast?", result, forecast)
    assert "forward cash" in q2.answer.lower() or "projected" in q2.answer.lower()

    print("[PASS] test_50_record_baseline_reconciliation passed successfully!")


def test_200_record_stress_test():
    generator = SyntheticFintechGenerator(seed=101)
    reconciler = NeuroSymbolicReconciler()

    raw = generator.generate_batch(record_count=200)
    gw_events = [GatewayEvent(**g) for g in raw["gateway_events"]]
    bank_recs = [BankStatementRecord(**b) for b in raw["bank_records"]]
    erp_invs = [ERPInvoice(**e) for e in raw["erp_invoices"]]
    tax_recs = [TaxRecord(**t) for t in raw["tax_records"]]

    result = reconciler.reconcile_batch(gw_events, bank_recs, erp_invs, tax_recs)

    print("\n200-Record Stress Test:")
    print(f"  * Processed: {result.total_records_processed} in {result.execution_time_ms} ms")
    print(f"  * Match Rate: {result.match_rate_pct}%")
    print(f"  * Precision Drift: INR {result.precision_drift_sum:.4f}")

    assert result.precision_drift_sum == 0.0
    print("[PASS] test_200_record_stress_test passed!")


if __name__ == "__main__":
    test_50_record_baseline_reconciliation()
    test_200_record_stress_test()
    print("\n>>> ALL RECONCILIATION & PIPELINE TESTS COMPLETED SUCCESSFULLY!")
