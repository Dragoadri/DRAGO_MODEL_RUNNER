"""GGUF file discovery and management"""
import re
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass

from ..utils.logger import get_logger
from ..utils.helpers import format_size
log = get_logger("gguf_manager")


@dataclass
class GGUFFile:
    """Represents a discovered GGUF model file"""
    path: Path
    name: str
    size_bytes: int

    @property
    def size_human(self) -> str:
        """Human-readable file size"""
        return format_size(self.size_bytes)

    @property
    def display_name(self) -> str:
        """Name without extension for display"""
        return self.path.stem

    @property
    def quantization(self) -> str:
        """Extract quantization level from filename (e.g. Q4_K_M, Q3_K_S)"""
        m = re.search(r'[_-](Q\d+[_-]?K?[_-]?[A-Z]?)', self.name, re.IGNORECASE)
        if m:
            return m.group(1).upper().replace('-', '_')
        # Check for fp16/fp32
        if re.search(r'fp16', self.name, re.IGNORECASE):
            return "FP16"
        if re.search(r'fp32', self.name, re.IGNORECASE):
            return "FP32"
        return ""

    @property
    def is_split(self) -> bool:
        """Check if this is a split/sharded GGUF file"""
        return bool(re.search(r'\d{5}-of-\d{5}', self.name))

    @property
    def split_info(self) -> Optional[Tuple[int, int]]:
        """Return (part_number, total_parts) if this is a split file, else None"""
        m = re.search(r'(\d{5})-of-(\d{5})', self.name)
        if m:
            return (int(m.group(1)), int(m.group(2)))
        return None


def detect_split_gguf(file_path: str) -> Optional[dict]:
    """Detect if a file is part of a split GGUF set.

    Returns a dict with split info if the file is split, None otherwise.
    Dict keys: part, total, found_parts, missing_parts, all_complete
    """
    path = Path(file_path)
    m = re.search(r'(\d{5})-of-(\d{5})', path.name)
    if not m:
        return None

    part_num = int(m.group(1))
    total_parts = int(m.group(2))

    # Build the expected pattern to find sibling parts
    prefix = path.name[:m.start()]
    suffix = path.name[m.end():]
    parent = path.parent

    found_parts = []
    missing_parts = []
    for i in range(1, total_parts + 1):
        expected_name = f"{prefix}{i:05d}-of-{total_parts:05d}{suffix}"
        expected_path = parent / expected_name
        if expected_path.exists():
            found_parts.append(i)
        else:
            missing_parts.append(i)

    return {
        "part": part_num,
        "total": total_parts,
        "found_parts": found_parts,
        "missing_parts": missing_parts,
        "all_complete": len(missing_parts) == 0,
    }


class GGUFManager:
    """Manages discovery and access to GGUF model files"""

    EXTENSIONS = {".gguf", ".bin"}

    def __init__(self, search_paths: Optional[List[str]] = None):
        self.search_paths = []
        if search_paths:
            for p in search_paths:
                expanded = Path(p).expanduser()
                if expanded.exists():
                    self.search_paths.append(expanded)

        # Always include common download/model directories
        extra_paths = [
            Path.home() / "ai-models",
            Path.home() / ".ollama" / "models",
            Path.home() / "models",
            Path.home() / "Descargas",
            Path.home() / "Downloads",
            Path.home() / "Escritorio",
            Path.home() / "Desktop",
            Path("/opt/models"),
        ]
        for p in extra_paths:
            if p.exists() and p.is_dir() and p not in self.search_paths:
                self.search_paths.append(p)

    def scan_directory(self, directory: Path, recursive: bool = True) -> List[GGUFFile]:
        """Scan a directory for GGUF files"""
        files = []
        directory = Path(directory).expanduser()

        if not directory.exists():
            return files

        pattern = "**/*" if recursive else "*"

        try:
            for ext in self.EXTENSIONS:
                for file_path in directory.glob(f"{pattern}{ext}"):
                    if file_path.is_file():
                        try:
                            files.append(GGUFFile(
                                path=file_path,
                                name=file_path.name,
                                size_bytes=file_path.stat().st_size
                            ))
                        except (OSError, PermissionError):
                            continue
        except PermissionError:
            log.warning("Permission denied scanning directory: %s", directory)
        except OSError as e:
            log.warning("OS error scanning directory %s: %s", directory, e)

        return sorted(files, key=lambda x: x.name.lower())

    def discover_all(self, recursive: bool = True) -> List[GGUFFile]:
        """Discover all GGUF files in configured search paths"""
        all_files = []
        seen_paths = set()

        for search_path in self.search_paths:
            try:
                for gguf in self.scan_directory(search_path, recursive):
                    if gguf.path not in seen_paths:
                        all_files.append(gguf)
                        seen_paths.add(gguf.path)
            except (PermissionError, OSError) as e:
                log.warning("Cannot scan %s: %s", search_path, e)
                continue

        return sorted(all_files, key=lambda x: x.name.lower())

    def add_search_path(self, path: str) -> bool:
        """Add a new search path"""
        expanded = Path(path).expanduser()
        if expanded.exists() and expanded.is_dir():
            if expanded not in self.search_paths:
                self.search_paths.append(expanded)
            return True
        return False

    def find_by_name(self, name: str) -> Optional[GGUFFile]:
        """Find a GGUF file by name (partial match)"""
        name_lower = name.lower()
        for gguf in self.discover_all():
            if name_lower in gguf.name.lower():
                return gguf
        return None
