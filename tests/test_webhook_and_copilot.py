"""
AegisPay-Controller: Test Suite for Razorpay Webhooks and CFO Copilot
Verifies HMAC-SHA256 signature verification, webhook simulation, and Copilot reasoning.
"""

import hmac
import hashlib
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_razorpay_webhook_valid_signature():
    secret = "whsec_aegispay_buildathon_2026"
    payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_webhook_999",
                    "amount": 500000,
                    "order_id": "order_test_999"
                }
            }
        },
        "created_at": 1711958400
    }

    body_bytes = json.dumps(payload).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

    resp = client.post(
        "/api/webhooks/razorpay",
        content=body_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": sig
        }
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["verified"] is True
    assert data["status"] == "ACCEPTED"
    assert data["event_summary"]["amount_inr"] == 5000.0


def test_razorpay_webhook_invalid_signature():
    payload = {"event": "payment.captured"}
    body_bytes = json.dumps(payload).encode("utf-8")

    resp = client.post(
        "/api/webhooks/razorpay",
        content=body_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": "invalid_tampered_signature_123"
        }
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["verified"] is False
    assert data["status"] == "VERIFICATION_FAILED"


def test_razorpay_webhook_simulation():
    resp = client.post("/api/webhooks/simulate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["verified"] is True
    assert data["event"] == "payment.captured"
    assert "signature" in data
    assert data["amount_inr"] > 0


def test_cfo_copilot_dispute_letter_generation():
    # First ensure a batch is loaded
    client.post("/api/reconcile", json={"record_count": 50})

    query_payload = {
        "query": "Draft formal dispute letter to Razorpay Support regarding fee overcharges",
        "api_key": None
    }

    resp = client.post("/api/copilot/query", json=query_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "Dispute & Recovery Notice" in data["answer"] or "Razorpay" in data["answer"]
    assert "RBI" in data["answer"] or "Discrepancy" in data["answer"]
