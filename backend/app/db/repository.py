"""
AegisPay-Controller: Database Repository
Provides helper operations for storing and querying batches, matches, exceptions, and merchant profiles.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.db.models import (
    MerchantModel,
    ReconciliationBatchModel,
    MatchedRecordModel,
    ExceptionRecordModel,
    AuditLogModel
)
from app.models.schemas import BatchReconciliationResult


DEFAULT_MERCHANTS = [
    {
        "mid": "MID_RZP_88392",
        "name": "Acme Retail Electronics Pvt Ltd",
        "business_type": "High-Volume UPI & Domestic Cards",
        "gstin": "27AABCA1234F1Z5",
        "contact_email": "cfo@acme-retail.com",
        "contact_name": "Priya Sharma",
        "default_scale": 50
    },
    {
        "mid": "MID_RZP_44019",
        "name": "Zenith D2C Fashion Store",
        "business_type": "High Refund Rate (D2C Fashion)",
        "gstin": "29AABCZ5678G2H7",
        "contact_email": "ops@zenith-fashion.com",
        "contact_name": "Arjun Mehta",
        "default_scale": 200
    },
    {
        "mid": "MID_RZP_71005",
        "name": "CloudSync Global SaaS",
        "business_type": "International Cards & Amex",
        "gstin": "06AABCC9012J3K1",
        "contact_email": "finance@cloudsync.io",
        "contact_name": "Deepak Verma",
        "default_scale": 100
    }
]


def seed_default_merchants(db: Session):
    """Inserts default merchants if not already present in the database"""
    for m in DEFAULT_MERCHANTS:
        existing = db.query(MerchantModel).filter(MerchantModel.mid == m["mid"]).first()
        if not existing:
            merchant = MerchantModel(
                mid=m["mid"],
                name=m["name"],
                business_type=m["business_type"],
                gstin=m["gstin"],
                contact_email=m["contact_email"],
                contact_name=m["contact_name"],
                default_scale=m["default_scale"]
            )
            db.add(merchant)
    db.commit()


def save_reconciliation_batch(
    db: Session,
    result: BatchReconciliationResult,
    merchant_mid: str = "MID_RZP_88392",
    performed_by: str = "Priya Sharma (CFO)"
) -> ReconciliationBatchModel:
    """Persists a full reconciliation batch, matched records, and exceptions into database"""
    
    # Ensure merchant exists
    merchant = db.query(MerchantModel).filter(MerchantModel.mid == merchant_mid).first()
    if not merchant:
        merchant = MerchantModel(
            mid=merchant_mid,
            name="Registered Merchant",
            business_type="E-Commerce D2C",
            gstin="27AABCR1000P1Z1",
            contact_email="admin@merchant.com",
            contact_name="Merchant Admin",
            default_scale=50
        )
        db.add(merchant)
        db.commit()

    # Parse timestamp safely
    if isinstance(result.timestamp, str):
        try:
            batch_time = datetime.fromisoformat(result.timestamp)
        except Exception:
            batch_time = datetime.now(timezone.utc)
    else:
        batch_time = datetime.now(timezone.utc)

    # Create Batch Record
    batch_record = ReconciliationBatchModel(
        batch_id=result.batch_id,
        merchant_mid=merchant_mid,
        timestamp=batch_time,
        total_records_processed=result.total_records_processed,
        matched_count=result.matched_count,
        exception_count=result.exception_count,
        match_rate_pct=result.match_rate_pct,
        precision_drift_sum=result.precision_drift_sum,
        total_gross_volume=result.total_gross_volume,
        total_bank_settled=result.total_bank_settled,
        total_mdr_fees_verified=result.total_mdr_fees_verified,
        total_gst_withheld=result.total_gst_withheld,
        total_tds_deducted=getattr(result, 'total_tds_deducted', 0.0),
        execution_time_ms=result.execution_time_ms,
        cryptographic_seal=result.cryptographic_seal,
        performed_by=performed_by
    )
    db.add(batch_record)

    # Insert Matched Records (cap to top 200 per batch to prevent SQLite lock on high scale 5,000 runs)
    matches_to_save = result.matches[:200] if len(result.matches) > 200 else result.matches
    for m in matches_to_save:
        order_id = m.gateway_events[0].order_id if m.gateway_events else (m.erp_invoices[0].order_id if m.erp_invoices else "N/A")
        customer_name = m.gateway_events[0].customer_name if m.gateway_events else (m.erp_invoices[0].customer_name if m.erp_invoices else "N/A")
        
        # Payment method
        if m.gateway_events and hasattr(m.gateway_events[0], 'method'):
            method_obj = m.gateway_events[0].method
            payment_method = method_obj.value if hasattr(method_obj, 'value') else str(method_obj)
        elif m.erp_invoices and hasattr(m.erp_invoices[0], 'payment_method'):
            method_obj = m.erp_invoices[0].payment_method
            payment_method = method_obj.value if hasattr(method_obj, 'value') else str(method_obj)
        else:
            payment_method = "UPI"

        gross_amount = m.proof.gross_sum if m.proof else sum(g.amount for g in m.gateway_events)
        mdr_fee = m.proof.mdr_total if m.proof else 0.0
        gst_tax = m.proof.gst_total if m.proof else 0.0
        tds_amount = m.proof.tds_total if m.proof else 0.0
        net_settlement = m.proof.calculated_net if m.proof else 0.0
        bank_utr = m.bank_records[0].utr if m.bank_records and hasattr(m.bank_records[0], 'utr') else "N/A"
        crypto_hash = m.proof.proof_hash if m.proof else "SEALED"

        match_entry = MatchedRecordModel(
            batch_id=result.batch_id,
            match_id=m.match_id,
            match_type=m.match_type.value if hasattr(m.match_type, 'value') else str(m.match_type),
            order_id=order_id,
            customer_name=customer_name,
            payment_method=payment_method,
            gross_amount=gross_amount,
            mdr_fee=mdr_fee,
            gst_tax=gst_tax,
            tds_amount=tds_amount,
            net_settlement=net_settlement,
            bank_utr=bank_utr,
            confidence_score=m.confidence,
            cryptographic_hash=crypto_hash
        )
        db.add(match_entry)

    # Insert Exceptions (cap to top 100 per batch)
    exceptions_to_save = result.exceptions[:100] if len(result.exceptions) > 100 else result.exceptions
    for e in exceptions_to_save:
        affected_orders = ", ".join(e.affected_order_ids) if e.affected_order_ids else "N/A"
        status_val = e.hitl_status.value if hasattr(e.hitl_status, 'value') else str(e.hitl_status)

        exc_entry = ExceptionRecordModel(
            batch_id=result.batch_id,
            exception_id=e.exception_id,
            root_cause=e.root_cause.value if hasattr(e.root_cause, 'value') else str(e.root_cause),
            severity=e.severity.value if hasattr(e.severity, 'value') else str(e.severity),
            order_id=affected_orders,
            variance_amount=e.variance_amount,
            suggested_action=e.recommended_action,
            status=status_val,
            confidence=0.95
        )
        db.add(exc_entry)

    # Insert Audit Log
    audit_entry = AuditLogModel(
        batch_id=result.batch_id,
        merchant_mid=merchant_mid,
        action="BATCH_RECONCILIATION_SEALED",
        performed_by=performed_by,
        sha256_seal=result.cryptographic_seal,
        details_json=f"Records: {result.total_records_processed}, Drift: INR {result.precision_drift_sum:.4f}"
    )
    db.add(audit_entry)

    db.commit()
    db.refresh(batch_record)
    return batch_record


def get_all_batches(db: Session, limit: int = 20) -> List[ReconciliationBatchModel]:
    """Retrieves most recent reconciliation batch runs"""
    return db.query(ReconciliationBatchModel).order_by(ReconciliationBatchModel.timestamp.desc()).limit(limit).all()


def get_batch_by_id(db: Session, batch_id: str) -> Optional[ReconciliationBatchModel]:
    """Retrieves single batch by its batch_id"""
    return db.query(ReconciliationBatchModel).filter(ReconciliationBatchModel.batch_id == batch_id).first()


def get_all_merchants(db: Session) -> List[MerchantModel]:
    """Retrieves all registered merchants"""
    return db.query(MerchantModel).order_by(MerchantModel.name.asc()).all()


def create_merchant(db: Session, merchant_dict: Dict[str, Any]) -> MerchantModel:
    """Registers a new merchant in the database"""
    merchant = MerchantModel(
        mid=merchant_dict.get("mid"),
        name=merchant_dict.get("name"),
        business_type=merchant_dict.get("business_type", "D2C Retail"),
        gstin=merchant_dict.get("gstin"),
        contact_email=merchant_dict.get("contact_email"),
        contact_name=merchant_dict.get("contact_name"),
        default_scale=merchant_dict.get("default_scale", 50)
    )
    db.add(merchant)
    db.commit()
    db.refresh(merchant)
    return merchant
