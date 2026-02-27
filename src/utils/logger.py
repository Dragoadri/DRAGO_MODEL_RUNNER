"""Centralized logging for DRAGO Model Runner"""
import logging
import logging.handlers
from pathlib import Path

_LOG_DIR = Path.home() / ".local" / "share" / "drago-model-runner" / "logs"
_LOG_FILE = _LOG_DIR / "drago.log"
_MAX_BYTES = 2 * 1024 * 1024  # 2 MB per file
_BACKUP_COUNT = 3
_initialized = False


def get_logger(name: str) -> logging.Logger:
    """Get a named logger with rotating file + console handlers."""
    global _initialized
    if not _initialized:
        _setup_root()
        _initialized = True
    return logging.getLogger(f"drago.{name}")


def _setup_root():
    """Configure the root drago logger once."""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("drago")
    root.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-5s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotating file handler
    fh = logging.handlers.RotatingFileHandler(
        _LOG_FILE, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # Console handler (WARNING+)
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(fmt)
    root.addHandler(ch)
