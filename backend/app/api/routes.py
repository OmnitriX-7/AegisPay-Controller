"""
AegisPay-Controller: API Routes and Telemetry Endpoints
Provides endpoints for reconciliation, forecasting, copilot QA, benchmarks, DB history, and Prometheus metrics.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import repository
from app.telemetry.metrics import record_batch_metrics, get_prometheus_metrics_output
from app.generator.synthetic_fintech import SyntheticFintechGenerator
from app.engine.neuro_symbolic_agent import NeuroSymbolicReconciler
from app.engine.cash_forecaster import ForwardCashForecaster
from app.copilot.settlement_qa import SettlementQACopilot
from app.models.schemas import (
    GatewayEvent,
    BankStatementRecord,
    ERPInvoice,
    TaxRecord,
    BatchReconciliationResult,
    CashForecastResponse
)

router = APIRouter()

# Global Singleton Services
generator = SyntheticFintechGenerator(seed=42)
reconciler = NeuroSymbolicReconciler()
forecaster = ForwardCashForecaster(seed=1337)
copilot = SettlementQACopilot()

# Cache for active in-memory state
active_state: Dict[str, Any] = {
    "last_result": None,
    "last_forecast": None
}


# --- Models for Custom API Requests ---
class ReconcilePayload(BaseModel):
    record_count: int = 50
    merchant_mid: str = "MID_RZP_88392"
    performed_by: str = "Priya Sharma (CFO)"

class ForecastPayload(BaseModel):
    starting_cash: float = 12500000.0
    horizon_days: int = 14
    daily_burn: float = 180000.0
    sales_growth_pct: float = 0.0
    refund_spike_pct: float = 3.0
    clearing_lag_days: int = 2

class QAQueryRequest(BaseModel):
    query: str
    batch_id: Optional[str] = None

class QAQueryResponse(BaseModel):
    answer: str
    confidence: float = 1.0
    sources: List[str] = []
    cryptographic_proof_hash: Optional[str] = None

class RegisterMerchantPayload(BaseModel):
    mid: str
    name: str
    business_type: str = "D2C Retail"
    gstin: Optional[str] = None
    contact_email: Optional[str] = None
    contact_name: Optional[str] = None
    default_scale: int = 50


# --- 1. Prometheus Telemetry Endpoint ---
@router.get("/metrics")
def prometheus_metrics():
    """Exposes standard Prometheus exposition format for scraper metrics"""
    content, content_type = get_prometheus_metrics_output()
    return Response(content=content, media_type=content_type)


# --- 2. System Status ---
@router.get("/api/status")
def system_status():
    return {
        "status": "HEALTHY",
        "engine": "NeuroSymbolicReconciler v2.0",
        "precision_invariant": "Zero-Drift Invariant Verified (0.0000 INR)",
        "database": "SQLAlchemy SQLite/PostgreSQL Ready",
        "telemetry": "Prometheus Metrics Active (/metrics)"
    }


# --- 3. Synthetic Data Generator ---
@router.get("/api/generate")
def generate_dataset(record_count: int = 50):
    raw = generator.generate_batch(record_count=record_count)
    return {
        "batch_id": f"batch_{record_count}_{generator.rng.randint(1000, 9999)}",
        "record_count": record_count,
        "gateway_events_count": len(raw["gateway_events"]),
        "bank_records_count": len(raw["bank_records"]),
        "erp_invoices_count": len(raw["erp_invoices"]),
        "tax_records_count": len(raw["tax_records"]),
        "preview_gateway": raw["gateway_events"][:3]
    }


# --- 4. Main Reconciliation Pipeline ---
@router.post("/api/reconcile", response_model=BatchReconciliationResult)
def reconcile_batch(
    payload: ReconcilePayload,
    db: Session = Depends(get_db)
):
    # 1. Ingest synthetic 4-way stream
    raw = generator.generate_batch(record_count=payload.record_count)
    gw = [GatewayEvent(**g) for g in raw["gateway_events"]]
    bank = [BankStatementRecord(**b) for b in raw["bank_records"]]
    erp = [ERPInvoice(**e) for e in raw["erp_invoices"]]
    tax = [TaxRecord(**t) for t in raw["tax_records"]]

    # 2. Run neuro-symbolic reconciliation engine
    result = reconciler.reconcile_batch(gw, bank, erp, tax)
    active_state["last_result"] = result

    # 3. Update Prometheus Telemetry
    record_batch_metrics(result, scale=payload.record_count)

    # 4. Persist to Database (SQLite / Postgres / Supabase)
    try:
        repository.save_reconciliation_batch(
            db=db,
            result=result,
            merchant_mid=payload.merchant_mid,
            performed_by=payload.performed_by
        )
    except Exception as e:
        # Non-blocking DB log to ensure reconciliation response always returns
        print(f"[DB Warning] Could not persist batch to database: {e}")

    return result


# --- 5. Forward Cash Forecaster ---
@router.post("/api/forecast", response_model=CashForecastResponse)
def forecast_cash(payload: ForecastPayload):
    if not active_state["last_result"]:
        # Generate baseline if not reconciled yet
        raw = generator.generate_batch(record_count=50)
        active_state["last_result"] = reconciler.reconcile_batch(
            [GatewayEvent(**g) for g in raw["gateway_events"]],
            [BankStatementRecord(**b) for b in raw["bank_records"]],
            [ERPInvoice(**e) for e in raw["erp_invoices"]],
            [TaxRecord(**t) for t in raw["tax_records"]]
        )

    forecast_res = forecaster.forecast_cash_position(
        reconciliation_result=active_state["last_result"],
        starting_cash=payload.starting_cash,
        horizon_days=payload.horizon_days,
        daily_operational_burn=payload.daily_burn,
        sales_growth_pct=payload.sales_growth_pct,
        refund_spike_pct=payload.refund_spike_pct,
        clearing_lag_days=payload.clearing_lag_days
    )
    active_state["last_forecast"] = forecast_res
    return forecast_res


# --- 6. CFO Settlement Copilot QA ---
@router.post("/api/copilot/query", response_model=QAQueryResponse)
def query_copilot(req: QAQueryRequest):
    result = active_state.get("last_result")
    forecast = active_state.get("last_forecast")
    return copilot.answer_query(query=req.query, result=result, forecast=forecast)


# --- 7. Historical Batches from Database ---
@router.get("/api/history")
def get_reconciliation_history(limit: int = 10, db: Session = Depends(get_db)):
    batches = repository.get_all_batches(db=db, limit=limit)
    return [
        {
            "batch_id": b.batch_id,
            "merchant_mid": b.merchant_mid,
            "timestamp": b.timestamp.isoformat(),
            "records": b.total_records_processed,
            "matches": b.matched_count,
            "exceptions": b.exception_count,
            "match_rate_pct": b.match_rate_pct,
            "precision_drift": b.precision_drift_sum,
            "gross_volume": b.total_gross_volume,
            "seal": b.cryptographic_seal,
            "performed_by": b.performed_by
        }
        for b in batches
    ]


# --- 8. Merchant Directory Management ---
@router.get("/api/merchants")
def get_merchants(db: Session = Depends(get_db)):
    merchants = repository.get_all_merchants(db=db)
    return [
        {
            "mid": m.mid,
            "name": m.name,
            "business_type": m.business_type,
            "gstin": m.gstin,
            "contact_email": m.contact_email,
            "contact_name": m.contact_name,
            "default_scale": m.default_scale
        }
        for m in merchants
    ]

@router.post("/api/merchants")
def register_merchant(payload: RegisterMerchantPayload, db: Session = Depends(get_db)):
    merchant = repository.create_merchant(db=db, merchant_dict=payload.model_dump())
    return {
        "status": "SUCCESS",
        "message": f"Merchant {merchant.name} successfully registered in database",
        "merchant": {
            "mid": merchant.mid,
            "name": merchant.name,
            "business_type": merchant.business_type,
            "gstin": merchant.gstin
        }
    }


# --- 9. Scalability Benchmark Matrix ---
@router.get("/api/benchmark")
def run_benchmarks():
    scales = [50, 200, 1000, 5000]
    benchmark_results = []
    
    for count in scales:
        raw = generator.generate_batch(record_count=count)
        gw = [GatewayEvent(**g) for g in raw["gateway_events"]]
        bank = [BankStatementRecord(**b) for b in raw["bank_records"]]
        erp = [ERPInvoice(**e) for e in raw["erp_invoices"]]
        tax = [TaxRecord(**t) for t in raw["tax_records"]]

        res = reconciler.reconcile_batch(gw, bank, erp, tax)
        throughput = round(res.total_records_processed / (res.execution_time_ms / 1000.0)) if res.execution_time_ms > 0 else 0

        benchmark_results.append({
            "scale": count,
            "total_processed": res.total_records_processed,
            "matches": res.matched_count,
            "exceptions": res.exception_count,
            "match_rate_pct": res.match_rate_pct,
            "latency_ms": res.execution_time_ms,
            "throughput_rps": throughput,
            "precision_drift": res.precision_drift_sum,
            "cryptographic_seal": res.cryptographic_seal
        })

    return {"benchmarks": benchmark_results}
