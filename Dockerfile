# ==============================================================================
# AegisPay-Controller: Production Dockerfile
# Autonomous Multi-Source Reconciliation & Forward Cash Forecaster
# Razorpay AI Buildathon 2026 - Track 04
# ==============================================================================

FROM python:3.12-slim

# Prevent python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Install python dependencies directly (wheels for linux-x86_64)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend, frontend, tests, and configuration
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY tests/ ./tests/

# Expose FastAPI & Prometheus port
EXPOSE 8000

# Native Python Healthcheck (no external curl binary needed)
HEALTHCHECK --interval=20s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/status')" || exit 1

# Start the unified AegisPay controller server
CMD ["python", "backend/run_server.py"]
