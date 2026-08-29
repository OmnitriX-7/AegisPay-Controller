"""
AegisPay-Controller: Custom Datasheet & CSV Parser
Ingests and normalizes real-world multi-format CSV/Excel datasheets for:
- Payment Gateway Settlements (Razorpay / Stripe / Cashfree)
- Core Bank Statements (HDFC / ICICI / SBI / Axis UTR credits)
- ERP Invoices (Zoho Books / Tally / SAP / NetSuite)
- Tax Portals (GST 2B / Section 194-O TDS Form 26AS)
"""

import csv
import io
from typing import Dict, List, Any
from datetime import datetime, timezone
from app.models.schemas import GatewayEvent, BankStatementRecord, ERPInvoice, TaxRecord
from app.models.ledger_types import PaymentMethod


def _clean_str(val: Any) -> str:
    if val is None:
        return ""
    return str(val).strip()


def _clean_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    s = str(val).replace(",", "").replace("₹", "").replace("$", "").strip()
    try:
        return round(float(s), 4)
    except ValueError:
        return default


def parse_gateway_csv(content: str) -> List[GatewayEvent]:
    """
    Parses gateway settlement CSV (Razorpay format or generic).
    """
    events: List[GatewayEvent] = []
    reader = csv.DictReader(io.StringIO(content))

    for row in reader:
        r = {k.strip().lower(): v for k, v in row.items() if k}

        order_id = r.get("order_id") or r.get("id") or r.get("payment_id") or f"ord_up_{len(events)+1}"
        amount = _clean_float(r.get("amount") or r.get("gross_amount") or r.get("gross") or 0.0)
        if amount <= 0:
            continue

        fee = _clean_float(r.get("fee") or r.get("mdr_fee") or r.get("fee_amount") or 0.0)
        gst = _clean_float(r.get("tax") or r.get("gst") or r.get("gst_on_fee") or r.get("gst_on_mdr") or 0.0)
        net = _clean_float(r.get("net") or r.get("net_amount") or r.get("settlement_amount") or (amount - fee - gst))
        mdr_rate = round(fee / amount, 4) if amount > 0 else 0.018

        method_raw = _clean_str(r.get("method") or r.get("payment_method") or "UPI").upper()
        method = PaymentMethod.UPI
        for pm in PaymentMethod:
            if pm.value in method_raw or method_raw in pm.value:
                method = pm
                break

        events.append(GatewayEvent(
            id=r.get("payment_id") or f"pay_{order_id}",
            order_id=order_id,
            amount=amount,
            currency="INR",
            method=method,
            mdr_rate=mdr_rate,
            mdr_fee=fee,
            gst_on_mdr=gst,
            net_amount=net,
            status="captured",
            settlement_batch_id=r.get("settlement_id") or r.get("batch_id") or "setl_custom_batch",
            customer_name=r.get("customer_name") or r.get("customer") or "Direct Customer",
            timestamp=r.get("timestamp") or r.get("created_at") or datetime.now(timezone.utc).isoformat()
        ))

    return events


def parse_bank_csv(content: str) -> List[BankStatementRecord]:
    """
    Parses bank account credit statement CSV (HDFC / ICICI / SBI format).
    """
    records: List[BankStatementRecord] = []
    reader = csv.DictReader(io.StringIO(content))

    for row in reader:
        r = {k.strip().lower(): v for k, v in row.items() if k}

        utr = r.get("utr") or r.get("reference_no") or r.get("txn_id") or f"UTR{len(records)+10001}"
        credit = _clean_float(r.get("credit") or r.get("credit_amount") or r.get("amount") or 0.0)
        if credit <= 0:
            continue

        desc = r.get("narration") or r.get("description") or f"CMS/RAZORPAY/{utr}"
        batch_ref = r.get("settlement_batch_id") or r.get("batch_id")
        if batch_ref and batch_ref not in desc:
            desc = f"{desc} {batch_ref}"

        records.append(BankStatementRecord(
            id=r.get("bank_txn_id") or f"bnk_{utr}",
            utr=utr,
            date=r.get("timestamp") or r.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            description=desc,
            amount=credit,
            type="CREDIT",
            clearing_channel=r.get("clearing_channel") or r.get("channel") or "NEFT"
        ))

    return records


def parse_erp_csv(content: str) -> List[ERPInvoice]:
    """
    Parses ERP invoice register CSV (Zoho / SAP / Tally).
    """
    invoices: List[ERPInvoice] = []
    reader = csv.DictReader(io.StringIO(content))

    for row in reader:
        r = {k.strip().lower(): v for k, v in row.items() if k}

        inv_no = r.get("invoice_number") or r.get("invoice_no") or f"INV-2026-{len(invoices)+1:04d}"
        total = _clean_float(r.get("total_amount") or r.get("total") or r.get("amount") or 0.0)
        if total <= 0:
            continue

        tax = _clean_float(r.get("tax_amount") or r.get("tax") or r.get("gst") or round(total * 0.18 / 1.18, 2))

        invoices.append(ERPInvoice(
            invoice_id=inv_no,
            order_id=r.get("order_id") or f"order_{len(invoices)+1:03d}",
            customer_name=r.get("customer_name") or "Retail Customer",
            gross_amount=total,
            tax_amount=tax,
            net_payable=total,
            status="PAID",
            issue_date=r.get("invoice_date") or r.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        ))

    return invoices


def parse_tax_csv(content: str) -> List[TaxRecord]:
    """
    Parses statutory tax ledger CSV (GST portal & Section 194-O TDS).
    """
    taxes: List[TaxRecord] = []
    reader = csv.DictReader(io.StringIO(content))

    for row in reader:
        r = {k.strip().lower(): v for k, v in row.items() if k}

        order_id = r.get("order_id") or f"order_{len(taxes)+1:03d}"
        taxable = _clean_float(r.get("taxable_value") or r.get("taxable_amount") or r.get("amount") or 0.0)
        tds = _clean_float(r.get("tds") or r.get("tds_194o") or r.get("tds_amount") or round(taxable * 0.01, 2))

        taxes.append(TaxRecord(
            id=f"tax_{order_id}",
            gstin=r.get("gstin") or "29AABCU9603R1ZM",
            section="194-O",
            order_id=order_id,
            gross_amount=taxable,
            tds_rate=0.01,
            tds_amount=tds,
            quarter="Q2-2026"
        ))

    return taxes
