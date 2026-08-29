"""
AegisPay-Controller: Data Models & Pydantic Schemas
Strict type validation and serialization for multi-source financial records.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date
from pydantic import BaseModel, Field
from .ledger_types import (
    TransactionType,
    PaymentMethod,
    ReconciliationStatus,
    ExceptionRootCause,
    ExceptionSeverity,
    ConfidenceLevel
)


# --- Input Sources ---

class GatewayEvent(BaseModel):
    """Event emitted by Razorpay Payment Gateway"""
    id: str = Field(description="Unique payment ID, e.g. pay_N8s9d7f02")
    order_id: str = Field(description="Order ID, e.g. order_9938210")
    amount: float = Field(description="Gross transaction amount in INR")
    currency: str = Field(default="INR")
    method: PaymentMethod = Field(description="Payment method used")
    mdr_rate: float = Field(description="Contractual MDR percentage, e.g. 0.018")
    mdr_fee: float = Field(description="MDR fee charged by gateway")
    gst_on_mdr: float = Field(description="18% GST on MDR fee")
    net_amount: float = Field(description="Net expected settlement: Gross - MDR - GST")
    status: str = Field(default="captured", description="captured, refunded, failed, disputed")
    timestamp: str = Field(description="ISO timestamp of capture")
    customer_name: str = Field(description="Payer name")
    customer_email: Optional[str] = None
    rrn: Optional[str] = Field(None, description="Bank Reference Number (RRN)")
    settlement_batch_id: Optional[str] = Field(None, description="Razorpay settlement batch id, e.g. setl_9831")
    dispute_id: Optional[str] = Field(None, description="Dispute reference if chargeback")


class BankStatementRecord(BaseModel):
    """Line item in Bank Statement / CAMT.053 feed"""
    id: str = Field(description="Bank line ID")
    utr: str = Field(description="Unique Transaction Reference (UTR) e.g. ICICR5202608220019284")
    date: str = Field(description="Value date YYYY-MM-DD")
    description: str = Field(description="Raw bank narration string")
    amount: float = Field(description="Transaction amount in INR")
    type: str = Field(default="CREDIT", description="CREDIT or DEBIT")
    balance_after: Optional[float] = None
    clearing_channel: str = Field(default="NEFT", description="NEFT, RTGS, IMPS, UPI, NACH")


class ERPInvoice(BaseModel):
    """Merchant ERP / Billing System Record (NetSuite / Tally / QuickBooks)"""
    invoice_id: str = Field(description="Invoice reference e.g. INV-2026-0891")
    order_id: str = Field(description="Corresponding order ID")
    customer_name: str = Field(description="Customer billing name")
    gross_amount: float = Field(description="Total invoice amount")
    tax_amount: float = Field(description="GST charged to customer")
    net_payable: float = Field(description="Gross invoice amount payable")
    status: str = Field(default="PAID", description="PAID, UNPAID, CANCELLED")
    issue_date: str = Field(description="Invoice date")
    due_date: Optional[str] = None


class TaxRecord(BaseModel):
    """Statutory Tax Subledger (GSTR-2B / Section 194-O TDS Withholding)"""
    id: str = Field(description="Tax line reference")
    gstin: str = Field(description="Merchant / Gateway GSTIN")
    section: str = Field(default="194-O", description="194-O (E-commerce TDS) or GST")
    order_id: Optional[str] = None
    settlement_batch_id: Optional[str] = None
    gross_amount: float = Field(description="Taxable base amount")
    tds_rate: float = Field(default=0.01, description="1% TDS or 18% GST")
    tds_amount: float = Field(description="Deducted TDS amount")
    quarter: str = Field(default="Q2-2026")


# --- Verification & Reconciliation Results ---

class InvariantProof(BaseModel):
    """Cryptographically auditable proof of mathematical invariance"""
    formula: str = "Net Bank Credit = Gross - MDR - GST - Refunds - Chargebacks - TDS"
    gross_sum: float
    mdr_total: float
    gst_total: float
    refunds_total: float
    chargebacks_total: float
    tds_total: float
    calculated_net: float
    bank_credit: float
    variance: float
    is_proven: bool
    proof_hash: str


class ReconciledMatch(BaseModel):
    """A verified multi-way reconciled transaction bundle"""
    match_id: str
    match_type: ReconciliationStatus
    confidence: float
    confidence_level: ConfidenceLevel
    gateway_events: List[GatewayEvent]
    bank_records: List[BankStatementRecord]
    erp_invoices: List[ERPInvoice]
    tax_records: List[TaxRecord] = []
    proof: InvariantProof
    audit_trace: List[str]
    reasoning: str


class ExceptionRecord(BaseModel):
    """An honest, un-cherry-picked exception with root-cause diagnosis"""
    exception_id: str
    root_cause: ExceptionRootCause
    severity: ExceptionSeverity
    variance_amount: float
    affected_order_ids: List[str]
    affected_utrs: List[str]
    raw_evidence: Dict[str, Any]
    description: str
    recommended_action: str
    hitl_status: str = Field(default="PENDING_REVIEW", description="PENDING_REVIEW, RESOLVED, DISMISSED")
    suggested_journal_entry: Optional[Dict[str, Any]] = None


class BatchReconciliationResult(BaseModel):
    """Complete summary of a reconciliation run across a dataset batch"""
    batch_id: str
    timestamp: str
    total_records_processed: int
    matched_count: int
    exception_count: int
    match_rate_pct: float
    precision_drift_sum: float
    total_gross_volume: float
    total_bank_settled: float
    total_mdr_fees_verified: float
    total_gst_withheld: float
    total_tds_deducted: float
    execution_time_ms: float
    matches: List[ReconciledMatch]
    exceptions: List[ExceptionRecord]
    cryptographic_seal: str


# --- Forecasting & Copilot Schemas ---

class CashForecastPoint(BaseModel):
    """Single date projection point"""
    date: str
    projected_cash_balance: float
    lower_bound_95ci: float
    upper_bound_95ci: float
    expected_gateway_settlements: float
    expected_payouts_and_burn: float
    reserve_holdback: float
    cash_at_risk: float


class CashForecastResponse(BaseModel):
    """Forward cash projection and liquidity health"""
    horizon_days: int
    starting_balance: float
    ending_projected_balance: float
    liquidity_health_score: float  # 0 to 100
    burn_rate_daily_avg: float
    unsettled_float_in_transit: float
    working_capital_buffer: float
    cash_at_risk_total: float
    projections: List[CashForecastPoint]
    liquidity_insights: List[str]


class CopilotQueryRequest(BaseModel):
    """Natural Language Finance Controller Query"""
    query: str
    session_id: Optional[str] = "cfo_session_01"


class CopilotQueryResponse(BaseModel):
    """Structured, verified Copilot response with audit evidence"""
    answer: str
    cited_match_ids: List[str] = []
    cited_exception_ids: List[str] = []
    itemized_breakdown: Optional[Dict[str, Any]] = None
    suggested_followups: List[str] = []
    confidence_score: float = 0.98


class ResolveExceptionPayload(BaseModel):
    """Human-in-the-loop exception resolution payload"""
    exception_id: str
    action: str = "APPROVE_JOURNAL"
    notes: Optional[str] = None
