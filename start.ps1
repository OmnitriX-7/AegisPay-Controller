# AegisPay-Controller 1-Click Launch Script (Windows PowerShell)
Write-Host "Starting AegisPay-Controller with Full Monitoring Stack (Prometheus + Loki + Grafana)..." -ForegroundColor Cyan

docker compose up -d

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Green
Write-Host " AEGISPAY-CONTROLLER PLATFORM ACTIVE AND RUNNING" -ForegroundColor Green
Write-Host " Track 04: AI Finance Controller - Razorpay AI Buildathon 2026" -ForegroundColor DarkGray
Write-Host "================================================================================" -ForegroundColor Green
Write-Host ""
Write-Host " ACCESS YOUR SERVICES IN THE BROWSER:" -ForegroundColor White
Write-Host ""
Write-Host " 1. Main Web Application UI:" -ForegroundColor Cyan
Write-Host "    http://localhost:8000" -ForegroundColor Yellow
Write-Host "    Purpose: Interactive 4-Way Reconciliation, DAG Flow, Cash Forecaster, CFO Copilot" -ForegroundColor Gray
Write-Host ""
Write-Host " 2. Prometheus Metrics Scraper:" -ForegroundColor Cyan
Write-Host "    http://localhost:9090" -ForegroundColor Yellow
Write-Host "    Purpose: Real-time telemetry scraper and query engine (Live feed at /metrics)" -ForegroundColor Gray
Write-Host ""
Write-Host " 3. Grafana Unified Monitoring Portal (Metrics + Loki Logs):" -ForegroundColor Cyan
Write-Host "    http://localhost:3000" -ForegroundColor Yellow
Write-Host "    Purpose: Dashboards, Prometheus graphs, and Loki Log Explorer (Default: admin / admin)" -ForegroundColor Gray
Write-Host ""
Write-Host " 4. Loki Log Ingestion Engine:" -ForegroundColor Cyan
Write-Host "    http://localhost:3100" -ForegroundColor Yellow
Write-Host "    Purpose: Centralized log aggregation and LogQL querying" -ForegroundColor Gray
Write-Host ""
Write-Host " 5. System Healthcheck API:" -ForegroundColor Cyan
Write-Host "    http://localhost:8000/api/status" -ForegroundColor Yellow
Write-Host "    Purpose: Status verification and zero-drift invariant proof" -ForegroundColor Gray
Write-Host ""
Write-Host "================================================================================" -ForegroundColor Green
Write-Host " To stop all services anytime: docker compose down" -ForegroundColor DarkGray
Write-Host "================================================================================" -ForegroundColor Green
