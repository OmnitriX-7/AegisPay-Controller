# AegisPay-Controller: Deployment & Architecture Guide

Track 04: Autonomous Multi-Source Financial Reconciliation & Forward Cash Forecaster  
**Razorpay AI Buildathon 2026**

---

## 🏗️ Architecture Stack

1. **Core Backend Engine**: Python 3.12, FastAPI, NumPy, Pydantic v2.
2. **Database Persistence Layer**: SQLAlchemy ORM with dual-engine support:
   - **SQLite** (Default, zero configuration, auto-created `aegispay.db`).
   - **PostgreSQL / Supabase** (Cloud enterprise ready via `DATABASE_URL`).
3. **Observability & Telemetry**: Standard Prometheus metrics registry exposed at `/metrics` + OpenTelemetry trace hooks.
4. **Containerization**: Multi-stage production `Dockerfile` + `docker-compose.yml`.

---

## 🚀 Option 1: Running with Docker (Recommended for Evaluators)

Launch the entire stack with a single command:

```bash
# Build and run the web application
docker compose up --build
```

Access points:
- **AegisPay Web Controller UI**: [http://localhost:8000](http://localhost:8000)
- **FastAPI Interactive API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Prometheus Telemetry Scraper**: [http://localhost:8000/metrics](http://localhost:8000/metrics)
- **Health Check**: [http://localhost:8000/api/status](http://localhost:8000/api/status)

### Running with Full Prometheus & Grafana Stack
```bash
docker compose --profile monitoring up --build
```
- **Grafana Dashboard**: [http://localhost:3000](http://localhost:3000) *(User: `admin`, Password: `aegispay`)*
- **Prometheus Server**: [http://localhost:9090](http://localhost:9090)

---

## 💻 Option 2: Running with Python Virtual Environment (`.venv`)

### 1. Create and Activate Virtual Environment
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Variables (Optional)
Copy `.env.example` to `.env`:
```bash
# To use Supabase or PostgreSQL, set DATABASE_URL:
# DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres
```

### 4. Run the Server
```bash
python backend/run_server.py
```

### 5. Run Invariant Verification & Test Suite
```bash
pytest tests/ -v
```

---

## 📊 Database Schema & ORM Entities

| Model | Table | Purpose |
| :--- | :--- | :--- |
| `MerchantModel` | `merchants` | Multi-tenant merchant profile, legal entity name, GSTIN, default batch scale. |
| `ReconciliationBatchModel` | `reconciliation_batches` | Batch header, total volume, match rate, ₹0.0000 precision residual, SHA-256 seal. |
| `MatchedRecordModel` | `matched_records` | 4-way matched records (Order ID, Bank UTR, Gross, MDR, GST, TDS, Net). |
| `ExceptionRecordModel` | `exceptions` | Honest exceptions with root causes, variances, and HITL approval states. |
| `AuditLogModel` | `audit_logs` | Immutable audit trail with SHA-256 cryptographic proof seals. |

---

## 📈 Prometheus Metrics Reference

| Metric Name | Type | Description |
| :--- | :--- | :--- |
| `aegispay_reconciliation_runs_total` | `Counter` | Total reconciliation pipeline runs executed. |
| `aegispay_records_processed_total` | `Counter` | Cumulative financial records reconciled across 4 sources. |
| `aegispay_matched_records_total` | `Counter` | Transactions successfully matched. |
| `aegispay_exceptions_total` | `Counter` | Honest exceptions classified by root cause. |
| `aegispay_gross_volume_audited_inr_total` | `Counter` | Total INR volume audited. |
| `aegispay_precision_drift_inr` | `Gauge` | Exact precision drift residual (guaranteed `0.0000`). |
| `aegispay_match_rate_percentage` | `Gauge` | Latest batch match rate percentage. |
| `aegispay_reconciliation_duration_seconds` | `Histogram` | End-to-end engine latency distribution. |
