"""
AegisPay-Controller: Database Persistence & Prometheus Telemetry Invariant Tests
Validates database storage, ACID invariants, and Prometheus metrics exposition.
"""

import sys
import os
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db import repository
from app.generator.synthetic_fintech import SyntheticFintechGenerator
from app.engine.neuro_symbolic_agent import NeuroSymbolicReconciler
from app.models.schemas import GatewayEvent, BankStatementRecord, ERPInvoice, TaxRecord
from app.telemetry.metrics import record_batch_metrics, get_prometheus_metrics_output


# In-Memory SQLite engine for isolated testing
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    repository.seed_default_merchants(session)
    yield session
    session.close()
    Base.metadata.drop_all(bind=test_engine)


def test_database_batch_persistence(db_session):
    """Verifies that a reconciliation batch and its invariant proofs are persisted accurately"""
    generator = SyntheticFintechGenerator(seed=42)
    reconciler = NeuroSymbolicReconciler()

    raw = generator.generate_batch(record_count=50)
    gw = [GatewayEvent(**g) for g in raw["gateway_events"]]
    bank = [BankStatementRecord(**b) for b in raw["bank_records"]]
    erp = [ERPInvoice(**e) for e in raw["erp_invoices"]]
    tax = [TaxRecord(**t) for t in raw["tax_records"]]

    result = reconciler.reconcile_batch(gw, bank, erp, tax)

    # 1. Save to Database
    saved_batch = repository.save_reconciliation_batch(
        db=db_session,
        result=result,
        merchant_mid="MID_RZP_88392",
        performed_by="Priya Sharma (CFO)"
    )

    assert saved_batch.batch_id == result.batch_id
    assert saved_batch.matched_count == result.matched_count
    assert saved_batch.exception_count == result.exception_count
    assert saved_batch.precision_drift_sum == 0.0
    assert saved_batch.cryptographic_seal == result.cryptographic_seal

    # 2. Query from Database
    queried = repository.get_batch_by_id(db=db_session, batch_id=result.batch_id)
    assert queried is not None
    assert len(queried.matches) == result.matched_count
    assert len(queried.exceptions) == result.exception_count


def test_merchant_directory_and_registration(db_session):
    """Verifies multi-tenant merchant seeding and new onboarding"""
    merchants = repository.get_all_merchants(db_session)
    assert len(merchants) >= 3, "Should have at least 3 default merchants seeded"

    # Register custom merchant
    new_m = repository.create_merchant(
        db=db_session,
        merchant_dict={
            "mid": "MID_CUSTOM_9988",
            "name": "OmniChannel Retail Pvt Ltd",
            "business_type": "D2C Retail",
            "gstin": "27AAACE9988H1Z2",
            "contact_email": "admin@omnichannel.com",
            "contact_name": "Rohan Deshmukh",
            "default_scale": 100
        }
    )
    assert new_m.mid == "MID_CUSTOM_9988"

    all_m = repository.get_all_merchants(db_session)
    assert any(m.mid == "MID_CUSTOM_9988" for m in all_m)


def test_prometheus_metrics_telemetry():
    """Verifies that Prometheus metrics are updated and properly formatted"""
    generator = SyntheticFintechGenerator(seed=42)
    reconciler = NeuroSymbolicReconciler()

    raw = generator.generate_batch(record_count=50)
    result = reconciler.reconcile_batch(
        [GatewayEvent(**g) for g in raw["gateway_events"]],
        [BankStatementRecord(**b) for b in raw["bank_records"]],
        [ERPInvoice(**e) for e in raw["erp_invoices"]],
        [TaxRecord(**t) for t in raw["tax_records"]]
    )

    record_batch_metrics(result, scale=50)

    output, content_type = get_prometheus_metrics_output()
    output_str = output.decode("utf-8")

    assert "aegispay_reconciliation_runs_total" in output_str
    assert "aegispay_records_processed_total" in output_str
    assert "aegispay_precision_drift_inr 0.0" in output_str
    assert "aegispay_matched_records_total" in output_str
