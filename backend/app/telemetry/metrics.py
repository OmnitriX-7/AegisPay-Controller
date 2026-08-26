"""
AegisPay-Controller: Prometheus Telemetry & Metrics Registry
Exposes Prometheus instrumentation for financial reconciliation, latency, and invariant verification.
"""

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST
)

# Shared Metrics Registry
REGISTRY = CollectorRegistry()

# 1. Reconciliation Volume & Run Counters
RECONCILIATION_RUNS_TOTAL = Counter(
    'aegispay_reconciliation_runs_total',
    'Total number of reconciliation pipeline executions',
    ['status', 'scale'],
    registry=REGISTRY
)

RECORDS_PROCESSED_TOTAL = Counter(
    'aegispay_records_processed_total',
    'Total 4-way financial records ingested and analyzed',
    registry=REGISTRY
)

MATCHED_RECORDS_TOTAL = Counter(
    'aegispay_matched_records_total',
    'Total transactions successfully matched across gateway, bank, ERP, and tax ledgers',
    registry=REGISTRY
)

EXCEPTIONS_TOTAL = Counter(
    'aegispay_exceptions_total',
    'Total honest exceptions detected by neuro-symbolic classifier',
    ['root_cause'],
    registry=REGISTRY
)

GROSS_VOLUME_AUDITED_INR = Counter(
    'aegispay_gross_volume_audited_inr_total',
    'Cumulative gross rupee volume audited by the controller',
    registry=REGISTRY
)

# 2. Financial Invariants & Health Gauges
PRECISION_DRIFT_GAUGE = Gauge(
    'aegispay_precision_drift_inr',
    'Current reconciliation batch precision residual in INR (guaranteed 0.0000)',
    registry=REGISTRY
)

MATCH_RATE_GAUGE = Gauge(
    'aegispay_match_rate_percentage',
    'Current batch reconciliation match rate percentage',
    registry=REGISTRY
)

LIQUIDITY_HEALTH_SCORE_GAUGE = Gauge(
    'aegispay_liquidity_health_score',
    'Treasury liquidity health score (0-100) from Monte Carlo forecaster',
    registry=REGISTRY
)

# 3. Performance & Latency Histograms
RECONCILIATION_DURATION_SECONDS = Histogram(
    'aegispay_reconciliation_duration_seconds',
    'Time spent executing the neuro-symbolic reconciliation pipeline in seconds',
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    registry=REGISTRY
)


def record_batch_metrics(result, scale: int = 50):
    """Updates Prometheus metrics upon completion of a batch run"""
    RECONCILIATION_RUNS_TOTAL.labels(status='success', scale=str(scale)).inc()
    RECORDS_PROCESSED_TOTAL.inc(result.total_records_processed)
    MATCHED_RECORDS_TOTAL.inc(result.matched_count)
    GROSS_VOLUME_AUDITED_INR.inc(result.total_gross_volume)
    
    PRECISION_DRIFT_GAUGE.set(result.precision_drift_sum)
    MATCH_RATE_GAUGE.set(result.match_rate_pct)
    RECONCILIATION_DURATION_SECONDS.observe(result.execution_time_ms / 1000.0)

    for exc in result.exceptions:
        cause_val = exc.root_cause.value if hasattr(exc.root_cause, 'value') else str(exc.root_cause)
        EXCEPTIONS_TOTAL.labels(root_cause=cause_val).inc()


def get_prometheus_metrics_output():
    """Generates prometheus exposition format text and content type"""
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
