"""
AegisPay-Controller: SQLAlchemy ORM Models
Defines schema for Merchants, Reconciliation Batches, Matches, Exceptions, and Audit Seals.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Text,
    ForeignKey
)
from sqlalchemy.orm import relationship
from app.db.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class MerchantModel(Base):
    """Registered Merchant Entity"""
    __tablename__ = "merchants"

    mid = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    business_type = Column(String(128), nullable=False)
    gstin = Column(String(32), nullable=True)
    contact_email = Column(String(128), nullable=True)
    contact_name = Column(String(128), nullable=True)
    default_scale = Column(Integer, default=50)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    batches = relationship("ReconciliationBatchModel", back_populates="merchant", cascade="all, delete-orphan")


class ReconciliationBatchModel(Base):
    """Historical Reconciliation Run Header"""
    __tablename__ = "reconciliation_batches"

    batch_id = Column(String(64), primary_key=True, index=True)
    merchant_mid = Column(String(64), ForeignKey("merchants.mid"), nullable=False, index=True)
    timestamp = Column(DateTime, default=utcnow, index=True)
    total_records_processed = Column(Integer, nullable=False)
    matched_count = Column(Integer, nullable=False)
    exception_count = Column(Integer, nullable=False)
    match_rate_pct = Column(Float, nullable=False)
    precision_drift_sum = Column(Float, default=0.0)
    total_gross_volume = Column(Float, nullable=False)
    total_bank_settled = Column(Float, nullable=False)
    total_mdr_fees_verified = Column(Float, nullable=False)
    total_gst_withheld = Column(Float, nullable=False)
    total_tds_deducted = Column(Float, default=0.0)
    execution_time_ms = Column(Float, nullable=False)
    cryptographic_seal = Column(String(64), nullable=False, index=True)
    performed_by = Column(String(128), default="System")

    # Relationships
    merchant = relationship("MerchantModel", back_populates="batches")
    matches = relationship("MatchedRecordModel", back_populates="batch", cascade="all, delete-orphan")
    exceptions = relationship("ExceptionRecordModel", back_populates="batch", cascade="all, delete-orphan")


class MatchedRecordModel(Base):
    """Reconciled 4-Way Match Detail"""
    __tablename__ = "matched_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(64), ForeignKey("reconciliation_batches.batch_id"), nullable=False, index=True)
    match_id = Column(String(64), nullable=False, index=True)
    match_type = Column(String(32), nullable=False)
    order_id = Column(String(64), nullable=False, index=True)
    customer_name = Column(String(128), nullable=False)
    payment_method = Column(String(64), nullable=False)
    gross_amount = Column(Float, nullable=False)
    mdr_fee = Column(Float, nullable=False)
    gst_tax = Column(Float, nullable=False)
    tds_amount = Column(Float, default=0.0)
    net_settlement = Column(Float, nullable=False)
    bank_utr = Column(String(64), nullable=True)
    confidence_score = Column(Float, default=1.0)
    cryptographic_hash = Column(String(64), nullable=True)

    batch = relationship("ReconciliationBatchModel", back_populates="matches")


class ExceptionRecordModel(Base):
    """Honest Exception Record"""
    __tablename__ = "exceptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(64), ForeignKey("reconciliation_batches.batch_id"), nullable=False, index=True)
    exception_id = Column(String(64), nullable=False, index=True)
    root_cause = Column(String(64), nullable=False)
    severity = Column(String(32), nullable=False)
    order_id = Column(String(64), nullable=False)
    variance_amount = Column(Float, nullable=False)
    suggested_action = Column(Text, nullable=True)
    status = Column(String(32), default="PENDING_REVIEW")
    confidence = Column(Float, default=0.95)

    batch = relationship("ReconciliationBatchModel", back_populates="exceptions")


class AuditLogModel(Base):
    """Immutable Audit Certificate & Action Seal"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(64), nullable=False, index=True)
    merchant_mid = Column(String(64), nullable=False, index=True)
    action = Column(String(64), nullable=False)
    performed_by = Column(String(128), nullable=False)
    timestamp = Column(DateTime, default=utcnow)
    sha256_seal = Column(String(64), nullable=False)
    details_json = Column(Text, nullable=True)
