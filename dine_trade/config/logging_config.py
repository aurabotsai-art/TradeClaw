"""Central logging configuration for DineTrade.

Features:
- Rotating log files under `logs/` at the project root.
- Standard format: timestamp, level, logger name, message.
- Optional JSON-style message support via structured logging in callers.

Usage:

    from dine_trade.config.logging_config import setup_logging

    logger = setup_logging("dine_trade.run_consensus_trade", log_file_prefix="consensus")
    logger.info("Starting pipeline...")
"""

from __future__ import annotations

import logging
import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional


def _logs_dir() -> Path:
    """Return the path to the shared logs directory, creating it if needed."""
    # logs/ folder at project root (two levels above this file)
    root = Path(__file__).resolve().parents[2]
    logs = root / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    return logs


def setup_logging(
    logger_name: str,
    *,
    log_file_prefix: Optional[str] = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """Configure and return a logger with rotating file + console handlers.

    - logger_name: e.g. "dine_trade.run_consensus_trade"
    - log_file_prefix: prefix for the log file name; defaults to logger_name
      with dots replaced by underscores.
    - level: logging level (default INFO).
    """
    logger = logging.getLogger(logger_name)

    if logger.handlers:
        # Already configured; just return it.
        return logger

    logger.setLevel(level)

    logs_dir = _logs_dir()
    if not log_file_prefix:
        log_file_prefix = logger_name.replace(".", "_")
    log_path = logs_dir / f"{log_file_prefix}.log"

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # Daily rotating file handler, keep ~7 days by default
    fh = TimedRotatingFileHandler(
        filename=str(log_path),
        when="midnight",
        backupCount=7,
        encoding="utf-8",
    )
    fh.setLevel(level)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Avoid propagating to root logger (prevents duplicate logs if root is configured)
    logger.propagate = False

    return logger

