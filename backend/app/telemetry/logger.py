"""
AegisPay-Controller: Centralized Logging Subsystem
Configures dual-destination structured logging to console (stdout) and rotating log files for Loki/Promtail ingestion.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Base data/logs directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
LOGS_DIR = BASE_DIR / "data" / "logs"
LOG_FILE = LOGS_DIR / "aegispay.log"

_initialized = False


def setup_logging(log_level: str = None) -> logging.Logger:
    """Configures root aegispay logger with console and rotating file handlers."""
    global _initialized
    level_name = (log_level or os.getenv("LOG_LEVEL", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    root_logger = logging.getLogger("aegispay")

    if not _initialized:
        root_logger.setLevel(level)
        root_logger.handlers.clear()

        log_format = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # 1. Console / Stdout handler (for terminal & docker logs)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(log_format)
        root_logger.addHandler(console_handler)

        # 2. File handler (for Promtail / Loki file scraping)
        try:
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                filename=str(LOG_FILE),
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5,
                encoding="utf-8"
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(log_format)
            root_logger.addHandler(file_handler)
        except Exception as err:
            console_handler.stream.write(f"[WARN] Failed to initialize file logger at {LOG_FILE}: {err}\n")

        root_logger.propagate = False
        _initialized = True

    return root_logger


def get_logger(module_name: str = "aegispay") -> logging.Logger:
    """Returns a namespaced child logger under aegispay."""
    setup_logging()
    if module_name == "aegispay":
        return logging.getLogger("aegispay")
    return logging.getLogger(f"aegispay.{module_name}")
