"""GGUF file discovery and management"""
import os
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class GGUFFile:
    """Represents a discovered GGUF model file"""
    path: Path
    name: str
    size_bytes: int

    @property
    def size_human(self) -> str:
        """Human-readable file size"""
        size = self.size_bytes
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    @property
    def display_name(self) -> str:
        """Name without extension for display"""
        return self.path.stem


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

        # Default paths if none provided
        if not self.search_paths:
            default_paths = [
                Path.home() / "ai-models",
                Path.home() / ".ollama" / "models",
                Path.home() / "models",
                Path("/opt/models"),
            ]
            self.search_paths = [p for p in default_paths if p.exists()]

    def scan_directory(self, directory: Path, recursive: bool = True) -> List[GGUFFile]:
        """Scan a directory for GGUF files"""
        files = []
        directory = Path(directory).expanduser()

        if not directory.exists():
            return files

        pattern = "**/*" if recursive else "*"

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

        return sorted(files, key=lambda x: x.name.lower())

    def discover_all(self, recursive: bool = True) -> List[GGUFFile]:
        """Discover all GGUF files in configured search paths"""
        all_files = []
        seen_paths = set()

        for search_path in self.search_paths:
            for gguf in self.scan_directory(search_path, recursive):
                if gguf.path not in seen_paths:
                    all_files.append(gguf)
                    seen_paths.add(gguf.path)

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
