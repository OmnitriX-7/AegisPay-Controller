"""
AegisPay-Controller: Synthetic FinTech Edge-Case Generator
Generates realistic multi-source datasets with parametric sizing (50 to 5,000+ records),
realistic MDR/GST math, multi-to-one batching, dirty narrations, and authentic edge cases.
"""

import random
import hashlib
from datetime import datetime, timedelta
from typing import Tuple, List, Dict, Any

from app.models.ledger_types import (
    PaymentMethod,
    STANDARD_MDR_RATES,
    GST_ON_MDR_RATE,
    TDS_194O_RATE
)
from app.models.schemas import (
    GatewayEvent,
    BankStatementRecord,
    ERPInvoice,
    TaxRecord
)

# Realistic Indian FinTech Mock Metadata
INDIAN_FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan", "Krishna", "Ishaan",
    "Shaurya", "Atharv", "Advik", "Pranav", "Advaith", "Ananya", "Diya", "Gauri", "Pari", "Anika",
    "Navya", "Angel", "Isha", "Avni", "Riya", "Myra", "Aadhya", "Saanvi", "Kiara", "Shanaya"
]
INDIAN_LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Mehta", "Iyer", "Nair", "Reddy", "Rao", "Gupta", "Agarwal",
    "Bose", "Banerjee", "Mukherjee", "Chatterjee", "Sen", "Das", "Choudhury", "Singh", "Kaur", "Deshmukh"
]
MERCHANT_GSTINS = ["29AABCB1234F1Z5", "27AACCR8921K1Z2", "07AAACR4091M1Z8", "33AABCR7712P1ZQ"]
BANK_PREFIXES = ["ICICR5", "HDFCR5", "SBINR5", "AXISR5", "KKBKR5", "YESBR5"]


class SyntheticFintechGenerator:
    """Generates interconnected 4-way financial records with known ground-truth invariants"""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def _generate_customer_name(self) -> str:
        first = self.rng.choice(INDIAN_FIRST_NAMES)
        last = self.rng.choice(INDIAN_LAST_NAMES)
        return f"{first} {last}"

    def _generate_utr(self, bank_prefix: str, day_offset: int) -> str:
        date_str = (datetime(2026, 8, 1) + timedelta(days=day_offset)).strftime("%Y%m%d")
        rand_suffix = f"{self.rng.randint(1000000, 9999999)}"
        return f"{bank_prefix}{date_str}{rand_suffix}"

    def generate_batch(self, record_count: int = 50) -> Dict[str, Any]:
        """
        Generates a coherent batch of Gateway, Bank, ERP, and Tax records.
        Guarantees realistic distributions and mathematically defined edge cases.
        """
        gateway_events: List[GatewayEvent] = []
        bank_records: List[BankStatementRecord] = []
        erp_invoices: List[ERPInvoice] = []
        tax_records: List[TaxRecord] = []

        base_date = datetime(2026, 8, 10, 9, 30, 0)
        running_bank_balance = 12500000.00  # ₹1.25 Cr starting balance

        # Determine scenario counts based on record_count
        num_clean = int(record_count * 0.55)
        num_clusters = max(2, int((record_count * 0.25) / 4))
        batch_cluster_size = 4
        num_fuzzy = max(3, int(record_count * 0.06))
        num_disputes = max(3, int(record_count * 0.06))
        num_exceptions = max(4, int(record_count * 0.08))
        
        # Calculate generated so far and ensure clean matches fill remainder to reach record_count
        generated_planned = (num_clusters * batch_cluster_size) + num_fuzzy + num_disputes + num_exceptions
        num_clean = max(num_clean, record_count - generated_planned + 5)

        order_counter = 1000
        invoice_counter = 5000

        # --- 1. Clean 1-to-1 Matches ---
        for i in range(num_clean):
            order_counter += 1
            invoice_counter += 1
            order_id = f"order_{order_counter}"
            invoice_id = f"INV-2026-{invoice_counter}"
            pay_id = f"pay_{hashlib.md5(f'{order_id}_{i}'.encode()).hexdigest()[:10]}"
            
            cust_name = self._generate_customer_name()
            gross_amount = round(self.rng.uniform(500.0, 45000.0), 2)
            method = self.rng.choice(list(PaymentMethod))
            mdr_rate = STANDARD_MDR_RATES[method]
            mdr_fee = round(gross_amount * mdr_rate, 2)
            gst_on_mdr = round(mdr_fee * GST_ON_MDR_RATE, 2)
            net_amount = round(gross_amount - mdr_fee - gst_on_mdr, 2)
            
            tx_time = base_date + timedelta(hours=i * 2, minutes=self.rng.randint(0, 59))
            bank_prefix = self.rng.choice(BANK_PREFIXES)
            utr = self._generate_utr(bank_prefix, i % 15)
            rrn = f"{self.rng.randint(100000000000, 999999999999)}"
            batch_id = f"setl_{order_counter}"

            # 1. Gateway Record
            gw_event = GatewayEvent(
                id=pay_id,
                order_id=order_id,
                amount=gross_amount,
                currency="INR",
                method=method,
                mdr_rate=mdr_rate,
                mdr_fee=mdr_fee,
                gst_on_mdr=gst_on_mdr,
                net_amount=net_amount,
                status="captured",
                timestamp=tx_time.isoformat(),
                customer_name=cust_name,
                customer_email=f"{cust_name.lower().replace(' ', '.')}@example.com",
                rrn=rrn,
                settlement_batch_id=batch_id
            )
            gateway_events.append(gw_event)

            # 2. Bank Record
            running_bank_balance += net_amount
            bank_rec = BankStatementRecord(
                id=f"bnk_{i+1:04d}",
                utr=utr,
                date=tx_time.strftime("%Y-%m-%d"),
                description=f"NEFT-RZP-SETTLEMENT-{batch_id}-{cust_name.upper().replace(' ', '/')}",
                amount=net_amount,
                type="CREDIT",
                balance_after=round(running_bank_balance, 2),
                clearing_channel="NEFT"
            )
            bank_records.append(bank_rec)

            # 3. ERP Invoice
            erp_inv = ERPInvoice(
                invoice_id=invoice_id,
                order_id=order_id,
                customer_name=cust_name,
                gross_amount=gross_amount,
                tax_amount=round(gross_amount * 0.18 / 1.18, 2),
                net_payable=gross_amount,
                status="PAID",
                issue_date=tx_time.strftime("%Y-%m-%d")
            )
            erp_invoices.append(erp_inv)

            # 4. Tax Record (Section 194-O)
            tds_amount = round(gross_amount * TDS_194O_RATE, 2)
            tax_rec = TaxRecord(
                id=f"tax_{i+1:04d}",
                gstin=self.rng.choice(MERCHANT_GSTINS),
                section="194-O",
                order_id=order_id,
                settlement_batch_id=batch_id,
                gross_amount=gross_amount,
                tds_rate=TDS_194O_RATE,
                tds_amount=tds_amount,
                quarter="Q2-2026"
            )
            tax_records.append(tax_rec)

        # --- 2. Multi-to-One Aggregated Batch Settlements ---
        # Group remaining batch orders into clusters of 4 orders per settlement batch
        for cluster_idx in range(num_clusters):
            batch_id = f"setl_batch_{cluster_idx + 100}"
            cluster_gross = 0.0
            cluster_mdr = 0.0
            cluster_gst = 0.0
            cluster_net = 0.0
            tx_time = base_date + timedelta(days=cluster_idx + 2, hours=14)
            bank_prefix = self.rng.choice(BANK_PREFIXES)
            utr = self._generate_utr(bank_prefix, (cluster_idx + 3) % 20)

            for order_idx in range(batch_cluster_size):
                order_counter += 1
                invoice_counter += 1
                order_id = f"order_{order_counter}"
                invoice_id = f"INV-2026-{invoice_counter}"
                pay_id = f"pay_{hashlib.md5(f'{order_id}_batch'.encode()).hexdigest()[:10]}"
                cust_name = self._generate_customer_name()
                gross_amount = round(self.rng.uniform(1200.0, 18000.0), 2)
                method = self.rng.choice([PaymentMethod.UPI, PaymentMethod.CREDIT_CARD_DOMESTIC, PaymentMethod.DEBIT_CARD])
                mdr_rate = STANDARD_MDR_RATES[method]
                mdr_fee = round(gross_amount * mdr_rate, 2)
                gst_on_mdr = round(mdr_fee * GST_ON_MDR_RATE, 2)
                net_amount = round(gross_amount - mdr_fee - gst_on_mdr, 2)

                cluster_gross += gross_amount
                cluster_mdr += mdr_fee
                cluster_gst += gst_on_mdr
                cluster_net += net_amount

                gw_event = GatewayEvent(
                    id=pay_id,
                    order_id=order_id,
                    amount=gross_amount,
                    currency="INR",
                    method=method,
                    mdr_rate=mdr_rate,
                    mdr_fee=mdr_fee,
                    gst_on_mdr=gst_on_mdr,
                    net_amount=net_amount,
                    status="captured",
                    timestamp=tx_time.isoformat(),
                    customer_name=cust_name,
                    customer_email=f"{cust_name.lower().replace(' ', '.')}@example.com",
                    settlement_batch_id=batch_id
                )
                gateway_events.append(gw_event)

                erp_inv = ERPInvoice(
                    invoice_id=invoice_id,
                    order_id=order_id,
                    customer_name=cust_name,
                    gross_amount=gross_amount,
                    tax_amount=round(gross_amount * 0.18 / 1.18, 2),
                    net_payable=gross_amount,
                    status="PAID",
                    issue_date=tx_time.strftime("%Y-%m-%d")
                )
                erp_invoices.append(erp_inv)

            # Single aggregated Bank credit for the whole batch
            cluster_net = round(cluster_net, 2)
            running_bank_balance += cluster_net
            bank_rec = BankStatementRecord(
                id=f"bnk_batch_{cluster_idx+1:04d}",
                utr=utr,
                date=tx_time.strftime("%Y-%m-%d"),
                description=f"CMS/RZP-AGGREGATED-BATCH/{batch_id}/ORDERS-{batch_cluster_size}/MUMBAI",
                amount=cluster_net,
                type="CREDIT",
                balance_after=round(running_bank_balance, 2),
                clearing_channel="RTGS"
            )
            bank_records.append(bank_rec)

        # --- 3. Fuzzy Narration & Truncated Names ---
        for f_idx in range(num_fuzzy):
            order_counter += 1
            invoice_counter += 1
            order_id = f"order_{order_counter}"
            invoice_id = f"INV-2026-{invoice_counter}"
            pay_id = f"pay_{hashlib.md5(f'{order_id}_fuzz'.encode()).hexdigest()[:10]}"
            full_name = self._generate_customer_name()
            # Messy / Truncated Narration: e.g. "S. Sharma" or "VIVAAN P." or "UPI/CR/582910/VIVAAN"
            truncated_name = f"{full_name.split()[0][0]}. {full_name.split()[1]}"
            gross_amount = round(self.rng.uniform(2500.0, 15000.0), 2)
            method = PaymentMethod.UPI
            mdr_rate = 0.0
            mdr_fee = 0.0
            gst_on_mdr = 0.0
            net_amount = gross_amount

            tx_time = base_date + timedelta(days=4, hours=f_idx + 1)
            utr = self._generate_utr("YESBR5", 5)
            batch_id = f"setl_fz_{order_counter}"

            gw_event = GatewayEvent(
                id=pay_id,
                order_id=order_id,
                amount=gross_amount,
                currency="INR",
                method=method,
                mdr_rate=mdr_rate,
                mdr_fee=mdr_fee,
                gst_on_mdr=gst_on_mdr,
                net_amount=net_amount,
                status="captured",
                timestamp=tx_time.isoformat(),
                customer_name=full_name,
                customer_email=f"{full_name.lower().replace(' ', '.')}@example.com",
                settlement_batch_id=batch_id
            )
            gateway_events.append(gw_event)

            running_bank_balance += net_amount
            bank_rec = BankStatementRecord(
                id=f"bnk_fuzz_{f_idx+1:04d}",
                utr=utr,
                date=tx_time.strftime("%Y-%m-%d"),
                description=f"UPI/CR/948201928401/{truncated_name.upper()}/RZP-PAY/{order_id}",
                amount=net_amount,
                type="CREDIT",
                balance_after=round(running_bank_balance, 2),
                clearing_channel="UPI"
            )
            bank_records.append(bank_rec)

            erp_inv = ERPInvoice(
                invoice_id=invoice_id,
                order_id=order_id,
                customer_name=full_name,
                gross_amount=gross_amount,
                tax_amount=round(gross_amount * 0.18 / 1.18, 2),
                net_payable=gross_amount,
                status="PAID",
                issue_date=tx_time.strftime("%Y-%m-%d")
            )
            erp_invoices.append(erp_inv)

        # --- 4. Refunds and Chargeback Disputes ---
        for d_idx in range(num_disputes):
            order_counter += 1
            invoice_counter += 1
            order_id = f"order_{order_counter}"
            invoice_id = f"INV-2026-{invoice_counter}"
            pay_id = f"pay_{hashlib.md5(f'{order_id}_disp'.encode()).hexdigest()[:10]}"
            cust_name = self._generate_customer_name()
            gross_amount = round(self.rng.uniform(6000.0, 22000.0), 2)
            method = PaymentMethod.CREDIT_CARD_DOMESTIC
            mdr_rate = 0.018
            mdr_fee = round(gross_amount * mdr_rate, 2)
            gst_on_mdr = round(mdr_fee * GST_ON_MDR_RATE, 2)
            refund_amount = round(gross_amount * 0.5, 2) # 50% partial refund
            net_amount = round(gross_amount - mdr_fee - gst_on_mdr - refund_amount, 2)

            tx_time = base_date + timedelta(days=6, hours=d_idx)
            utr = self._generate_utr("HDFCR5", 7)
            batch_id = f"setl_disp_{order_counter}"

            gw_event = GatewayEvent(
                id=pay_id,
                order_id=order_id,
                amount=gross_amount,
                currency="INR",
                method=method,
                mdr_rate=mdr_rate,
                mdr_fee=mdr_fee,
                gst_on_mdr=gst_on_mdr,
                net_amount=net_amount,
                status="partially_refunded",
                timestamp=tx_time.isoformat(),
                customer_name=cust_name,
                customer_email=f"{cust_name.lower().replace(' ', '.')}@example.com",
                settlement_batch_id=batch_id,
                dispute_id=f"disp_rf_{order_counter}"
            )
            gateway_events.append(gw_event)

            running_bank_balance += net_amount
            bank_rec = BankStatementRecord(
                id=f"bnk_disp_{d_idx+1:04d}",
                utr=utr,
                date=tx_time.strftime("%Y-%m-%d"),
                description=f"NEFT-RZP-ADJUSTED-SETL/{batch_id}/PARTIAL-REFUND-ADJ",
                amount=net_amount,
                type="CREDIT",
                balance_after=round(running_bank_balance, 2),
                clearing_channel="NEFT"
            )
            bank_records.append(bank_rec)

            erp_inv = ERPInvoice(
                invoice_id=invoice_id,
                order_id=order_id,
                customer_name=cust_name,
                gross_amount=gross_amount,
                tax_amount=round(gross_amount * 0.18 / 1.18, 2),
                net_payable=gross_amount,
                status="PAID",
                issue_date=tx_time.strftime("%Y-%m-%d")
            )
            erp_invoices.append(erp_inv)

        # --- 5. Authentic Injected Exceptions (The Honest Exception List) ---
        exception_types = [
            "MDR_RATE_DISCREPANCY",
            "BANK_TIMING_LAG_T_PLUS_N",
            "UNMATCHED_CHARGEBACK_CLAWBACK",
            "MULTI_TO_ONE_AGGREGATION_RESIDUAL",
            "GST_TDS_WITHHOLDING_GAP",
            "DUPLICATE_GATEWAY_WEBHOOK",
            "UNCLAIMED_BANK_CREDIT"
        ]

        for e_idx in range(num_exceptions):
            order_counter += 1
            invoice_counter += 1
            order_id = f"order_{order_counter}"
            invoice_id = f"INV-2026-{invoice_counter}"
            pay_id = f"pay_exc_{hashlib.md5(f'{order_id}_exc'.encode()).hexdigest()[:8]}"
            cust_name = self._generate_customer_name()
            exc_type = exception_types[e_idx % len(exception_types)]

            tx_time = base_date + timedelta(days=8, hours=e_idx)

            if exc_type == "MDR_RATE_DISCREPANCY":
                # Gateway billed 2.8% instead of contracted 1.8%
                gross = 50000.00
                contract_mdr = 0.018
                billed_mdr = 0.028  # Overcharged
                billed_mdr_fee = round(gross * billed_mdr, 2)
                billed_gst = round(billed_mdr_fee * 0.18, 2)
                net = round(gross - billed_mdr_fee - billed_gst, 2)
                
                gw = GatewayEvent(
                    id=pay_id,
                    order_id=order_id,
                    amount=gross,
                    currency="INR",
                    method=PaymentMethod.CREDIT_CARD_DOMESTIC,
                    mdr_rate=billed_mdr,  # Discrepancy!
                    mdr_fee=billed_mdr_fee,
                    gst_on_mdr=billed_gst,
                    net_amount=net,
                    status="captured",
                    timestamp=tx_time.isoformat(),
                    customer_name=cust_name,
                    settlement_batch_id=f"setl_exc_{e_idx}"
                )
                gateway_events.append(gw)
                bank_records.append(BankStatementRecord(
                    id=f"bnk_exc_{e_idx+1:04d}",
                    utr=self._generate_utr("ICICR5", 9),
                    date=tx_time.strftime("%Y-%m-%d"),
                    description=f"NEFT-RZP-SETL-setl_exc_{e_idx}-MDR-DIFF",
                    amount=net,
                    type="CREDIT",
                    balance_after=round(running_bank_balance + net, 2)
                ))
                erp_invoices.append(ERPInvoice(
                    invoice_id=invoice_id,
                    order_id=order_id,
                    customer_name=cust_name,
                    gross_amount=gross,
                    tax_amount=round(gross * 0.18 / 1.18, 2),
                    net_payable=gross,
                    issue_date=tx_time.strftime("%Y-%m-%d")
                ))

            elif exc_type == "BANK_TIMING_LAG_T_PLUS_N":
                # Settled on gateway on Friday, but Bank credit not yet arrived (Pending T+2 clearing)
                gross = 32000.00
                gw = GatewayEvent(
                    id=pay_id,
                    order_id=order_id,
                    amount=gross,
                    currency="INR",
                    method=PaymentMethod.NETBANKING,
                    mdr_rate=0.015,
                    mdr_fee=480.0,
                    gst_on_mdr=86.40,
                    net_amount=31433.60,
                    status="captured",
                    timestamp=(base_date + timedelta(days=14, hours=18)).isoformat(),
                    customer_name=cust_name,
                    settlement_batch_id=f"setl_lag_{e_idx}"
                )
                gateway_events.append(gw)
                erp_invoices.append(ERPInvoice(
                    invoice_id=invoice_id,
                    order_id=order_id,
                    customer_name=cust_name,
                    gross_amount=gross,
                    tax_amount=round(gross * 0.18 / 1.18, 2),
                    net_payable=gross,
                    issue_date=gw.timestamp[:10]
                ))
                # Note: Bank statement entry is missing intentionally (Timing lag)

            elif exc_type == "UNMATCHED_CHARGEBACK_CLAWBACK":
                # Bank deducted ₹15,000 for chargeback clawback without matching ERP invoice status
                clawback_amount = 15000.00
                running_bank_balance -= clawback_amount
                bank_records.append(BankStatementRecord(
                    id=f"bnk_claw_{e_idx+1:04d}",
                    utr=self._generate_utr("AXISR5", 10),
                    date=tx_time.strftime("%Y-%m-%d"),
                    description=f"DR-CHARGEBACK-CLAWBACK-DISP_9981-CASE-ICICI",
                    amount=clawback_amount,
                    type="DEBIT",
                    balance_after=round(running_bank_balance, 2)
                ))

            elif exc_type == "GST_TDS_WITHHOLDING_GAP":
                # 1% TDS deducted (₹250), but ERP booked full ₹25,000 without tax withholding ledger entry
                gross = 25000.00
                gw = GatewayEvent(
                    id=pay_id,
                    order_id=order_id,
                    amount=gross,
                    currency="INR",
                    method=PaymentMethod.UPI,
                    mdr_rate=0.0,
                    mdr_fee=0.0,
                    gst_on_mdr=0.0,
                    net_amount=gross - 250.00,  # ₹250 TDS deducted
                    status="captured",
                    timestamp=tx_time.isoformat(),
                    customer_name=cust_name,
                    settlement_batch_id=f"setl_tds_{e_idx}"
                )
                gateway_events.append(gw)
                bank_records.append(BankStatementRecord(
                    id=f"bnk_tds_{e_idx+1:04d}",
                    utr=self._generate_utr("SBINR5", 11),
                    date=tx_time.strftime("%Y-%m-%d"),
                    description=f"NEFT-RZP-SETL-setl_tds_{e_idx}-TDS-DEDUCTED",
                    amount=gross - 250.00,
                    type="CREDIT",
                    balance_after=round(running_bank_balance + (gross - 250.0), 2)
                ))
                erp_invoices.append(ERPInvoice(
                    invoice_id=invoice_id,
                    order_id=order_id,
                    customer_name=cust_name,
                    gross_amount=gross,
                    tax_amount=round(gross * 0.18 / 1.18, 2),
                    net_payable=gross,  # Expected 25,000 without accounting for 250 TDS!
                    issue_date=tx_time.strftime("%Y-%m-%d")
                ))

            elif exc_type == "DUPLICATE_GATEWAY_WEBHOOK":
                # Gateway fired 2 duplicate events for the same order
                gross = 8500.00
                gw1 = GatewayEvent(
                    id=pay_id,
                    order_id=order_id,
                    amount=gross,
                    currency="INR",
                    method=PaymentMethod.UPI,
                    mdr_rate=0.0,
                    mdr_fee=0.0,
                    gst_on_mdr=0.0,
                    net_amount=gross,
                    status="captured",
                    timestamp=tx_time.isoformat(),
                    customer_name=cust_name,
                    settlement_batch_id=f"setl_dup_{e_idx}"
                )
                gw2 = GatewayEvent(
                    id=f"{pay_id}_dup",
                    order_id=order_id,
                    amount=gross,
                    currency="INR",
                    method=PaymentMethod.UPI,
                    mdr_rate=0.0,
                    mdr_fee=0.0,
                    gst_on_mdr=0.0,
                    net_amount=gross,
                    status="captured",
                    timestamp=(tx_time + timedelta(seconds=12)).isoformat(),
                    customer_name=cust_name,
                    settlement_batch_id=f"setl_dup_{e_idx}"
                )
                gateway_events.extend([gw1, gw2])
                bank_records.append(BankStatementRecord(
                    id=f"bnk_dup_{e_idx+1:04d}",
                    utr=self._generate_utr("HDFCR5", 12),
                    date=tx_time.strftime("%Y-%m-%d"),
                    description=f"UPI/CR/9823019/{order_id}/RZP",
                    amount=gross,  # Bank only credited once
                    type="CREDIT",
                    balance_after=round(running_bank_balance + gross, 2)
                ))
                erp_invoices.append(ERPInvoice(
                    invoice_id=invoice_id,
                    order_id=order_id,
                    customer_name=cust_name,
                    gross_amount=gross,
                    tax_amount=round(gross * 0.18 / 1.18, 2),
                    net_payable=gross,
                    issue_date=tx_time.strftime("%Y-%m-%d")
                ))

            elif exc_type == "UNCLAIMED_BANK_CREDIT":
                # Direct IMPS credit in bank without any gateway or ERP order reference
                unclaimed_amount = 18450.00
                running_bank_balance += unclaimed_amount
                bank_records.append(BankStatementRecord(
                    id=f"bnk_uncl_{e_idx+1:04d}",
                    utr=self._generate_utr("KKBKR5", 13),
                    date=tx_time.strftime("%Y-%m-%d"),
                    description=f"IMPS-DIRECT-TRANSFER-REF-992019-UNKNOWN-REMITTER",
                    amount=unclaimed_amount,
                    type="CREDIT",
                    balance_after=round(running_bank_balance, 2)
                ))

        # Shuffle lists to simulate authentic asynchronous arrival
        self.rng.shuffle(gateway_events)
        self.rng.shuffle(bank_records)
        self.rng.shuffle(erp_invoices)
        self.rng.shuffle(tax_records)

        return {
            "gateway_events": [g.model_dump() for g in gateway_events],
            "bank_records": [b.model_dump() for b in bank_records],
            "erp_invoices": [e.model_dump() for e in erp_invoices],
            "tax_records": [t.model_dump() for t in tax_records],
            "metadata": {
                "total_gateway_records": len(gateway_events),
                "total_bank_records": len(bank_records),
                "total_erp_records": len(erp_invoices),
                "total_tax_records": len(tax_records),
                "generated_at": datetime.now().isoformat()
            }
        }
