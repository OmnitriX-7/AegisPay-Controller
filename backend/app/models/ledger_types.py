"""
AegisPay-Controller: Core Ledger Types & Enums
Deterministic FinTech Invariants and Exception Taxonomy
"""

from enum import Enum


class TransactionType(str, Enum):
    PAYMENT = "PAYMENT"
    REFUND = "REFUND"
    CHARGEBACK = "CHARGEBACK"
    PAYOUT = "PAYOUT"
    MDR_FEE = "MDR_FEE"
    GST_TAX = "GST_TAX"
    TDS_WITHHOLDING = "TDS_WITHHOLDING"
    ADJUSTMENT = "ADJUSTMENT"
    RESERVE_HOLD = "RESERVE_HOLD"


class PaymentMethod(str, Enum):
    UPI = "UPI"
    CREDIT_CARD_DOMESTIC = "CREDIT_CARD_DOMESTIC"
    CREDIT_CARD_INTL = "CREDIT_CARD_INTL"
    DEBIT_CARD = "DEBIT_CARD"
    NETBANKING = "NETBANKING"
    BNPL_WALLET = "BNPL_WALLET"


class ReconciliationStatus(str, Enum):
    PERFECT_MATCH = "PERFECT_MATCH"               # 100% Deterministic exact match across 3+ sources
    FUZZY_RESOLVED = "FUZZY_RESOLVED"             # Neuro-symbolic match with dirty narration / name truncation resolved
    BATCH_DECOMPOSED = "BATCH_DECOMPOSED"         # Multi-to-one aggregation matched with exact net balance
    DISPUTE_RECONCILED = "DISPUTE_RECONCILED"     # Chargeback / partial refund reconciled with dispute ID
    UNRESOLVED_EXCEPTION = "UNRESOLVED_EXCEPTION" # True exception needing Human-In-The-Loop review


class ExceptionRootCause(str, Enum):
    MDR_RATE_DISCREPANCY = "MDR_RATE_DISCREPANCY"                       # Contractual vs gateway billed rate mismatch
    BANK_TIMING_LAG_T_PLUS_N = "BANK_TIMING_LAG_T_PLUS_N"               # Gateway settled on T+0, bank clearing on T+2
    UNMATCHED_CHARGEBACK_CLAWBACK = "UNMATCHED_CHARGEBACK_CLAWBACK"     # Bank clawback without ERP dispute confirmation
    MULTI_TO_ONE_AGGREGATION_RESIDUAL = "MULTI_TO_ONE_AGGREGATION_RESIDUAL" # Batch deposit missing 1 or more line items
    NAME_INVERSION_OR_TRUNCATION = "NAME_INVERSION_OR_TRUNCATION"       # Truncated or inverted customer/merchant names
    GST_TDS_WITHHOLDING_GAP = "GST_TDS_WITHHOLDING_GAP"                 # 1% TDS under Sec 194-O not accounted by ERP
    DUPLICATE_GATEWAY_WEBHOOK = "DUPLICATE_GATEWAY_WEBHOOK"             # Double webhook firing without duplicate bank credit
    UNCLAIMED_BANK_CREDIT = "UNCLAIMED_BANK_CREDIT"                     # Direct bank transfer with missing order reference


class ExceptionSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ConfidenceLevel(str, Enum):
    PROVEN_DETERMINISTIC = "PROVEN_DETERMINISTIC"   # Score: 1.0 (Zero residual)
    AGENTIC_VERIFIED = "AGENTIC_VERIFIED"           # Score: 0.90 - 0.99
    PROBABLE_MATCH = "PROBABLE_MATCH"               # Score: 0.75 - 0.89
    ACTION_REQUIRED = "ACTION_REQUIRED"             # Score: < 0.75


# Standard MDR Rate Card by Payment Method
STANDARD_MDR_RATES = {
    PaymentMethod.UPI: 0.000,                  # 0% for standard UPI
    PaymentMethod.DEBIT_CARD: 0.009,           # 0.9% for RuPay / Visa Debit
    PaymentMethod.CREDIT_CARD_DOMESTIC: 0.018, # 1.8% Domestic Credit
    PaymentMethod.CREDIT_CARD_INTL: 0.028,     # 2.8% International Amex/Visa
    PaymentMethod.NETBANKING: 0.015,           # 1.5% Netbanking
    PaymentMethod.BNPL_WALLET: 0.020           # 2.0% Wallets / PayLater
}

GST_ON_MDR_RATE = 0.18                         # 18% GST on all gateway processing fees
TDS_194O_RATE = 0.01                           # 1% TDS on E-commerce Gross
