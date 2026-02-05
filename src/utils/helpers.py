"""Helper utilities"""
import re
import threading
from pathlib import Path
from typing import Callable, Any


def expand_path(path: str) -> Path:
    """Expand user home and resolve path"""
    return Path(path).expanduser().resolve()


def format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def safe_filename(name: str) -> str:
    """Convert string to safe filename"""
    # Remove invalid characters
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # Replace spaces with hyphens
    name = re.sub(r'\s+', '-', name)
    # Remove multiple hyphens
    name = re.sub(r'-+', '-', name)
    # Lowercase and trim
    return name.lower().strip('-')[:50]


def run_async(func: Callable, *args, **kwargs) -> threading.Thread:
    """Run function in background thread"""
    thread = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
    thread.start()
    return thread


class AsyncResult:
    """Container for async operation result"""

    def __init__(self):
        self.result: Any = None
        self.error: Exception = None
        self.completed = threading.Event()

    def set_result(self, result: Any):
        self.result = result
        self.completed.set()

    def set_error(self, error: Exception):
        self.error = error
        self.completed.set()

    def wait(self, timeout: float = None) -> Any:
        self.completed.wait(timeout)
        if self.error:
            raise self.error
        return self.result
