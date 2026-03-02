"""Centralized logging for DRAGO Model Runner"""
import logging
import logging.handlers
import threading
from collections import deque
from pathlib import Path
from typing import List

_LOG_DIR = Path.home() / ".local" / "share" / "drago-model-runner" / "logs"
_LOG_FILE = _LOG_DIR / "drago.log"
_MAX_BYTES = 2 * 1024 * 1024  # 2 MB per file
_BACKUP_COUNT = 3
_initialized = False

# In-memory ring buffer for UI log display
_memory_handler: "MemoryRingHandler | None" = None


class MemoryRingHandler(logging.Handler):
    """Keeps the last *maxlen* log records in a thread-safe deque.

    The system panel (or any UI component) can call ``get_recent()``
    to retrieve formatted log lines without reading from disk.
    """

    def __init__(self, maxlen: int = 200, level: int = logging.INFO):
        super().__init__(level)
        self._buffer: deque[str] = deque(maxlen=maxlen)
        self._lock_rw = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            with self._lock_rw:
                self._buffer.append(msg)
        except Exception:
            self.handleError(record)

    def get_recent(self, count: int = 50) -> List[str]:
        """Return up to *count* most recent formatted log lines."""
        with self._lock_rw:
            items = list(self._buffer)
        return items[-count:]

    def clear(self) -> None:
        with self._lock_rw:
            self._buffer.clear()


def get_logger(name: str) -> logging.Logger:
    """Get a named logger with rotating file + console handlers."""
    global _initialized
    if not _initialized:
        _setup_root()
        _initialized = True
    return logging.getLogger(f"drago.{name}")


def get_memory_handler() -> "MemoryRingHandler | None":
    """Return the in-memory ring handler (available after first get_logger call)."""
    return _memory_handler


def _setup_root():
    """Configure the root drago logger once."""
    global _memory_handler

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

    # In-memory ring buffer (INFO+) for UI display
    _memory_handler = MemoryRingHandler(maxlen=200, level=logging.INFO)
    _memory_handler.setFormatter(fmt)
    root.addHandler(_memory_handler)
