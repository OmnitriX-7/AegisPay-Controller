"""
AegisPay-Controller: Server Launcher
Track 04: Autonomous Finance & Reconciliation Agent
Razorpay AI Buildathon 2026
"""

import sys
import os
import uvicorn

# Ensure the backend directory is in sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    print("=" * 63)
    print(f">> Starting AegisPay-Controller Engine on http://{host}:{port}")
    print("   Track 04: AI Finance Controller - Razorpay AI Buildathon 2026")
    print("=" * 63)
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
