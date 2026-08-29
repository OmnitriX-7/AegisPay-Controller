"""
AegisPay-Controller: Test Suite for Custom Datasheet (CSV) Ingestion
Verifies parsing of Gateway, Bank, ERP, and Tax CSV files and end-to-end reconciliation.
"""

from fastapi.testclient import TestClient
from app.main import app
from app.generator.csv_parser import (
    parse_gateway_csv,
    parse_bank_csv,
    parse_erp_csv,
    parse_tax_csv
)

client = TestClient(app)

SAMPLE_GATEWAY_CSV = """order_id,payment_id,amount,method,fee,tax,net,settlement_id,customer_name
order_test_01,pay_01,1000.00,UPI,0.00,0.00,1000.00,setl_test_batch,Rohan Mehta
order_test_02,pay_02,2500.00,DEBIT_CARD,22.50,4.05,2473.45,setl_test_batch,Sneha Roy
"""

SAMPLE_BANK_CSV = """utr,credit_amount,clearing_channel,settlement_batch_id,narration
UTR_TEST_01,1000.00,UPI,setl_test_batch,CMS/RAZORPAY/order_test_01
UTR_TEST_02,2473.45,NEFT,setl_test_batch,CMS/RAZORPAY/order_test_02
"""

SAMPLE_ERP_CSV = """invoice_number,order_id,customer_name,total_amount
INV-2026-001,order_test_01,Rohan Mehta,1000.00
INV-2026-002,order_test_02,Sneha Roy,2500.00
"""

SAMPLE_TAX_CSV = """order_id,gstin,taxable_value,tds_194o
order_test_01,27AAACE1234H1Z8,847.46,0.00
order_test_02,27AAACE1234H1Z8,2118.64,0.00
"""


def test_csv_individual_parsers():
    gw = parse_gateway_csv(SAMPLE_GATEWAY_CSV)
    assert len(gw) == 2
    assert gw[0].order_id == "order_test_01"
    assert gw[0].amount == 1000.00
    assert gw[1].net_amount == 2473.45

    bank = parse_bank_csv(SAMPLE_BANK_CSV)
    assert len(bank) == 2
    assert bank[0].utr == "UTR_TEST_01"
    assert bank[0].amount == 1000.00

    erp = parse_erp_csv(SAMPLE_ERP_CSV)
    assert len(erp) == 2
    assert erp[0].invoice_id == "INV-2026-001"
    assert erp[1].gross_amount == 2500.00

    tax = parse_tax_csv(SAMPLE_TAX_CSV)
    assert len(tax) == 2
    assert tax[0].tds_amount == 0.00


def test_api_ingest_csv_endpoint():
    payload = {
        "gateway_csv": SAMPLE_GATEWAY_CSV,
        "bank_csv": SAMPLE_BANK_CSV,
        "erp_csv": SAMPLE_ERP_CSV,
        "tax_csv": SAMPLE_TAX_CSV,
        "merchant_mid": "MID_RZP_88392",
        "performed_by": "Test Suite Auditor"
    }

    resp = client.post("/api/ingest/csv", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_records_processed"] >= 2
    assert data["precision_drift_sum"] == 0.0
    assert data["cryptographic_seal"] is not None
    assert len(data["matches"]) >= 1


def test_api_sample_csv_download():
    for stream in ["gateway", "bank", "erp", "tax"]:
        resp = client.get(f"/api/samples/download/{stream}")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")
        assert len(resp.text) > 50
