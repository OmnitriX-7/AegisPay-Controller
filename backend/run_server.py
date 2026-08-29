"""
AegisPay-Controller: Server Launcher
Track 04: Autonomous Finance & Reconciliation Agent
Razorpay AI Buildathon 2026
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Ensure .env is loaded from project root
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

import uvicorn

# Ensure the backend directory is in sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    banner = f"""
================================================================================
 🛡️  AEGISPAY-CONTROLLER PLATFORM READY
    Track 04: AI Finance Controller — Razorpay AI Buildathon 2026
================================================================================

 🌐 ACTIVE SERVICE ENDPOINTS:

  1. 💻 Main Web Application:
     👉 http://localhost:{port}
     Description: Full interactive UI, 4-Way Reconciliation, Cash Forecaster & CFO Copilot.

  2. 📊 Prometheus Metrics Scraper:
     👉 http://localhost:9090
     Description: Real-time telemetry query interface & latency histogram scraper.
     (Direct metrics feed: http://localhost:{port}/metrics)

  3. 📈 Grafana Telemetry Dashboard:
     👉 http://localhost:3000
     Description: Visual monitoring analytics (Default Login: admin / admin).

  4. 🔍 System Healthcheck API:
     👉 http://localhost:{port}/api/status
     Description: Zero-drift invariant verification & database readiness status.

================================================================================
"""
    print(banner)
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
