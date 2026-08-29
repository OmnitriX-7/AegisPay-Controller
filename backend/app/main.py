"""
AegisPay-Controller: FastAPI Application Entry Point
Track 04: Autonomous Multi-Source Reconciliation & Forward Cash Forecaster
Razorpay AI Buildathon 2026
"""

import os
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables from .env file at workspace root
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.db.database import init_db
from app.telemetry.logger import get_logger

logger = get_logger("server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database tables & default seeds
    logger.info("Initializing AegisPay-Controller database and default seeds...")
    init_db()
    logger.info("AegisPay-Controller initialized successfully and ready for transactions.")
    yield
    # Shutdown: clean up if needed
    logger.info("AegisPay-Controller shutting down cleanly.")


app = FastAPI(
    title="AegisPay-Controller",
    description="Autonomous Multi-Source Reconciliation, Zero-Drift Invariant Engine, & Forward Cash Forecaster",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware for development & production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API and Telemetry Router
app.include_router(api_router)

# Mount Frontend Static Assets
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/healthz")
async def health_check():
    return {"status": "HEALTHY", "service": "aegispay-controller"}
