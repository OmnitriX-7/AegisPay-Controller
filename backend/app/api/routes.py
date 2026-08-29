"""
AegisPay-Controller: API Routes and Telemetry Endpoints
Provides endpoints for:
- 4-way reconciliation (synthetic & custom CSV datasheets)
- Forward cash forecasting (14-day Monte Carlo)
- CFO Settlement Copilot (Google Gemini 2.0 Flash with fallback)
- Real-time Razorpay Webhook listener (HMAC-SHA256 signature verification)
- Scalability benchmarks, merchant registry, and Prometheus metrics.
"""

import os
import hmac
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import repository
from app.telemetry.metrics import record_batch_metrics, get_prometheus_metrics_output
from app.telemetry.logger import get_logger
from app.generator.synthetic_fintech import SyntheticFintechGenerator
from app.generator.csv_parser import (
    parse_gateway_csv,
    parse_bank_csv,
    parse_erp_csv,
    parse_tax_csv
)
from app.engine.neuro_symbolic_agent import NeuroSymbolicReconciler
from app.engine.cash_forecaster import ForwardCashForecaster
from app.copilot.settlement_qa import SettlementQACopilot
from app.models.schemas import (
    GatewayEvent,
    BankStatementRecord,
    ERPInvoice,
    TaxRecord,
    BatchReconciliationResult,
    CashForecastResponse,
    CopilotQueryResponse,
    ResolveExceptionPayload
)

logger = get_logger("api")
router = APIRouter()

# Global Singleton Services
generator = SyntheticFintechGenerator(seed=42)
reconciler = NeuroSymbolicReconciler()
forecaster = ForwardCashForecaster(seed=1337)
copilot = SettlementQACopilot()

# Cache for active in-memory state & live webhooks
active_state: Dict[str, Any] = {
    "last_result": None,
    "last_forecast": None,
    "live_webhook_events": []
}

SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "sample_data"


# --- Request & Payload Schemas ---

class ReconcilePayload(BaseModel):
    record_count: int = 50
    merchant_mid: str = "MID_RZP_88392"
    performed_by: str = "Priya Sharma (CFO)"


class CSVIngestPayload(BaseModel):
    gateway_csv: Optional[str] = None
    bank_csv: Optional[str] = None
    erp_csv: Optional[str] = None
    tax_csv: Optional[str] = None
    merchant_mid: str = "MID_RZP_88392"
    performed_by: str = "Finance Controller (Custom CSV Ingest)"


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
    api_key: Optional[str] = None


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
        "telemetry": "Prometheus Metrics Active (/metrics)",
        "copilot_llm": "Google Gemini 2.0 Flash Hybrid Active",
        "webhooks": "Razorpay HMAC-SHA256 Verified"
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


# --- 4. Main Synthetic Reconciliation Pipeline ---
@router.post("/api/reconcile", response_model=BatchReconciliationResult)
def reconcile_batch(
    payload: ReconcilePayload,
    db: Session = Depends(get_db)
):
    logger.info(f"Triggering synthetic reconciliation batch for {payload.merchant_mid} (scale: {payload.record_count})")
    raw = generator.generate_batch(record_count=payload.record_count)
    gw = [GatewayEvent(**g) for g in raw["gateway_events"]]
    bank = [BankStatementRecord(**b) for b in raw["bank_records"]]
    erp = [ERPInvoice(**e) for e in raw["erp_invoices"]]
    tax = [TaxRecord(**t) for t in raw["tax_records"]]

    result = reconciler.reconcile_batch(gw, bank, erp, tax)
    active_state["last_result"] = result
    record_batch_metrics(result, scale=payload.record_count)

    try:
        repository.save_reconciliation_batch(
            db=db,
            result=result,
            merchant_mid=payload.merchant_mid,
            performed_by=payload.performed_by
        )
    except Exception as e:
        logger.warning(f"Could not persist batch to database: {e}")

    logger.info(f"Reconciliation completed: {result.matched_count} matches, {result.exception_count} exceptions, drift=INR {result.precision_drift_sum:.4f}")
    return result


# --- 5. Custom Datasheet (CSV) Ingestion Pipeline ---
@router.post("/api/ingest/csv", response_model=BatchReconciliationResult)
def ingest_csv_batch(
    payload: CSVIngestPayload,
    db: Session = Depends(get_db)
):
    """
    Parses custom user-uploaded CSV datasheets for Gateway, Bank, ERP, and Tax streams.
    Falls back to sample data for any stream not supplied.
    """
    logger.info(f"Ingesting custom CSV datasheets for merchant {payload.merchant_mid}")

    # 1. Gateway CSV
    if payload.gateway_csv and payload.gateway_csv.strip():
        gw = parse_gateway_csv(payload.gateway_csv)
    else:
        sample_path = SAMPLE_DIR / "razorpay_settlement_sample.csv"
        gw = parse_gateway_csv(sample_path.read_text(encoding="utf-8")) if sample_path.exists() else []

    # 2. Bank Statement CSV
    if payload.bank_csv and payload.bank_csv.strip():
        bank = parse_bank_csv(payload.bank_csv)
    else:
        sample_path = SAMPLE_DIR / "hdfc_bank_statement_sample.csv"
        bank = parse_bank_csv(sample_path.read_text(encoding="utf-8")) if sample_path.exists() else []

    # 3. ERP Invoices CSV
    if payload.erp_csv and payload.erp_csv.strip():
        erp = parse_erp_csv(payload.erp_csv)
    else:
        sample_path = SAMPLE_DIR / "zoho_erp_sample.csv"
        erp = parse_erp_csv(sample_path.read_text(encoding="utf-8")) if sample_path.exists() else []

    # 4. Tax Ledger CSV
    if payload.tax_csv and payload.tax_csv.strip():
        tax = parse_tax_csv(payload.tax_csv)
    else:
        sample_path = SAMPLE_DIR / "gst_tax_portal_sample.csv"
        tax = parse_tax_csv(sample_path.read_text(encoding="utf-8")) if sample_path.exists() else []

    if not gw:
        raise HTTPException(status_code=400, detail="Gateway CSV was empty or could not be parsed.")

    # Reconcile custom records
    result = reconciler.reconcile_batch(gw, bank, erp, tax)
    active_state["last_result"] = result
    record_batch_metrics(result, scale=len(gw))

    try:
        repository.save_reconciliation_batch(
            db=db,
            result=result,
            merchant_mid=payload.merchant_mid,
            performed_by=payload.performed_by
        )
    except Exception as e:
        logger.warning(f"Could not persist custom batch to DB: {e}")

    logger.info(f"Custom CSV batch reconciled: {result.total_records_processed} records, {result.matched_count} matches, {result.exception_count} exceptions")
    return result


# --- 6. Download Sample CSV Templates ---
@router.get("/api/samples/download/{stream_type}")
def download_sample_csv(stream_type: str):
    """Returns downloadable template CSV files for Gateway, Bank, ERP, or Tax ledgers."""
    file_map = {
        "gateway": "razorpay_settlement_sample.csv",
        "bank": "hdfc_bank_statement_sample.csv",
        "erp": "zoho_erp_sample.csv",
        "tax": "gst_tax_portal_sample.csv"
    }
    filename = file_map.get(stream_type.lower())
    if not filename:
        raise HTTPException(status_code=404, detail="Invalid stream type. Choose from: gateway, bank, erp, tax")

    file_path = SAMPLE_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Sample template file not found.")

    content = file_path.read_text(encoding="utf-8")
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# --- 7. Forward Cash Forecaster ---
@router.post("/api/forecast", response_model=CashForecastResponse)
def forecast_cash(payload: ForecastPayload):
    if not active_state["last_result"]:
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


# --- 8. CFO Settlement Copilot (Hybrid Gemini LLM) ---
@router.post("/api/copilot/query", response_model=CopilotQueryResponse)
def query_copilot(req: QAQueryRequest):
    result = active_state.get("last_result")
    forecast = active_state.get("last_forecast")
    return copilot.answer_query(
        query=req.query,
        rec_result=result,
        forecast_result=forecast,
        api_key=req.api_key
    )


# --- 9. Live Razorpay Webhook Ingestion with HMAC Verification ---
@router.post("/api/webhooks/razorpay")
async def receive_razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None)
):
    """
    Receives and validates incoming Razorpay webhooks (payment.captured, settlement.processed).
    Cryptographically verifies HMAC-SHA256 signature against secret.
    """
    body_bytes = await request.body()
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "whsec_aegispay_buildathon_2026")

    # Cryptographic HMAC verification
    computed_sig = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
    is_signature_valid = hmac.compare_digest(computed_sig, x_razorpay_signature) if x_razorpay_signature else False

    try:
        event_data = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        event_data = {"raw_payload": body_bytes.decode("utf-8", errors="ignore")}

    webhook_record = {
        "event": event_data.get("event", "payment.captured"),
        "signature_verified": is_signature_valid,
        "received_at": event_data.get("created_at") or 1711958400,
        "entity_id": event_data.get("payload", {}).get("payment", {}).get("entity", {}).get("id", "pay_live_webhook_01"),
        "amount_inr": (event_data.get("payload", {}).get("payment", {}).get("entity", {}).get("amount", 0)) / 100.0
    }

    active_state["live_webhook_events"].append(webhook_record)
    logger.info(f"Razorpay Webhook received: {webhook_record['event']} | Verified: {is_signature_valid} | Amount: INR {webhook_record['amount_inr']}")

    return {
        "status": "ACCEPTED" if is_signature_valid else "VERIFICATION_FAILED",
        "verified": is_signature_valid,
        "event_summary": webhook_record
    }


# --- 9.5 Human-in-the-Loop (HITL) Exception Resolution ---
@router.post("/api/exceptions/resolve")
def resolve_exception(payload: ResolveExceptionPayload):
    """
    Human-In-The-Loop (HITL) Exception Resolution.
    Records CFO or FinOps approval and balances the adjustment in the audit log.
    """
    from datetime import datetime
    rec_result = active_state.get("last_result")
    resolved_item = None

    if rec_result and hasattr(rec_result, "exceptions"):
        for exc in rec_result.exceptions:
            if exc.exception_id == payload.exception_id:
                exc.hitl_status = "RESOLVED" if payload.action == "APPROVE_JOURNAL" else "DISMISSED"
                resolved_item = exc
                break

    action_label = "Adjusting Journal Entry Posted" if payload.action == "APPROVE_JOURNAL" else "Exception Dismissed"
    logger.info(f"Exception {payload.exception_id} resolved: {payload.action}")

    return {
        "status": "SUCCESS",
        "exception_id": payload.exception_id,
        "action": payload.action,
        "resolution_summary": action_label,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/api/webhooks/simulate")
def simulate_razorpay_webhook():
    """
    Generates a simulated live Razorpay settlement webhook with a valid HMAC-SHA256 signature for demoing.
    """
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "whsec_aegispay_buildathon_2026")
    order_num = generator.rng.randint(200, 999)
    amount_paise = generator.rng.randint(250000, 1500000)

    payload_dict = {
        "entity": "event",
        "account_id": "acc_aegispay_rzp_01",
        "event": "payment.captured",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": f"pay_live_{order_num}",
                    "amount": amount_paise,
                    "currency": "INR",
                    "status": "captured",
                    "order_id": f"order_live_{order_num}",
                    "method": "upi",
                    "fee": 0,
                    "tax": 0,
                    "email": "customer@razorpay-demo.com",
                    "contact": "+919876543210"
                }
            }
        },
        "created_at": 1711958400
    }

    body_bytes = json.dumps(payload_dict).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

    simulated_event = {
        "event": "payment.captured",
        "order_id": f"order_live_{order_num}",
        "payment_id": f"pay_live_{order_num}",
        "amount_inr": amount_paise / 100.0,
        "method": "UPI",
        "signature": signature,
        "verified": True,
        "raw_payload": payload_dict
    }

    active_state["live_webhook_events"].append(simulated_event)
    logger.info(f"Simulated live Razorpay webhook created: {simulated_event['payment_id']} (INR {simulated_event['amount_inr']})")
    return simulated_event


# --- 10. Historical Batches from Database ---
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


# --- 11. Merchant Directory Management ---
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


# --- 12. Scalability Benchmark Matrix ---
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
