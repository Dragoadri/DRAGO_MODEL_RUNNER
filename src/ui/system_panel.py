"""System Specifications Panel with auto-refresh, GPU monitoring, and diagnostics"""
import customtkinter as ctk
import subprocess
import threading
import os
import platform
import json
import shutil
from pathlib import Path
from typing import Dict, Optional, List

from .theme import COLORS, DECORATIONS, RADIUS
from .widgets import (
    MatrixFrame, MatrixScrollableFrame, MatrixLabel,
    TerminalHeader, MatrixProgressBar, MatrixButton
)


# Auto-refresh interval in milliseconds (30 seconds)
AUTO_REFRESH_INTERVAL = 30_000


class SystemInfo:
    """Gather system information"""

    @staticmethod
    def get_cpu_info() -> Dict:
        """Get CPU information"""
        info = {
            "name": "Unknown",
            "cores": os.cpu_count() or 0,
            "threads": os.cpu_count() or 0,
        }

        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        info["name"] = line.split(":")[1].strip()
                        break
        except Exception:
            info["name"] = platform.processor() or "Unknown CPU"

        return info

    @staticmethod
    def get_memory_info() -> Dict:
        """Get RAM information including swap"""
        info = {
            "total_gb": 0, "available_gb": 0, "used_percent": 0,
            "swap_total_gb": 0, "swap_used_gb": 0,
        }

        try:
            with open("/proc/meminfo", "r") as f:
                meminfo = {}
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        meminfo[parts[0].rstrip(":")] = int(parts[1])

                total_kb = meminfo.get("MemTotal", 0)
                available_kb = meminfo.get("MemAvailable", 0)

                info["total_gb"] = total_kb / (1024 * 1024)
                info["available_gb"] = available_kb / (1024 * 1024)
                info["used_percent"] = ((total_kb - available_kb) / total_kb * 100) if total_kb > 0 else 0

                swap_total = meminfo.get("SwapTotal", 0)
                swap_free = meminfo.get("SwapFree", 0)
                info["swap_total_gb"] = swap_total / (1024 * 1024)
                info["swap_used_gb"] = (swap_total - swap_free) / (1024 * 1024)
        except Exception:
            pass

        return info

    @staticmethod
    def get_gpu_info() -> Dict:
        """Get GPU information via nvidia-smi or rocm-smi"""
        info = {
            "available": False,
            "vendor": "",
            "name": "No GPU detected",
            "vram_total_gb": 0,
            "vram_used_gb": 0,
            "vram_free_gb": 0,
            "temperature": 0,
            "utilization": 0,
            "driver_version": "",
            "cuda_version": ""
        }

        # Try NVIDIA first
        if shutil.which("nvidia-smi"):
            try:
                result = subprocess.run(
                    ["nvidia-smi",
                     "--query-gpu=name,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu,driver_version",
                     "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    parts = result.stdout.strip().split(",")
                    if len(parts) >= 7:
                        info["available"] = True
                        info["vendor"] = "NVIDIA"
                        info["name"] = parts[0].strip()
                        info["vram_total_gb"] = float(parts[1].strip()) / 1024
                        info["vram_used_gb"] = float(parts[2].strip()) / 1024
                        info["vram_free_gb"] = float(parts[3].strip()) / 1024
                        info["temperature"] = int(parts[4].strip())
                        info["utilization"] = int(parts[5].strip().replace("%", ""))
                        info["driver_version"] = parts[6].strip()

                # Get CUDA version
                result3 = subprocess.run(
                    ["nvidia-smi"], capture_output=True, text=True, timeout=5
                )
                if result3.returncode == 0 and "CUDA Version:" in result3.stdout:
                    for line in result3.stdout.split("\n"):
                        if "CUDA Version:" in line:
                            cuda_part = line.split("CUDA Version:")[1].split()[0]
                            info["cuda_version"] = cuda_part.strip()
                            break
            except Exception:
                pass

        # Try AMD ROCm if NVIDIA not found
        if not info["available"] and shutil.which("rocm-smi"):
            try:
                result = subprocess.run(
                    ["rocm-smi", "--showproductname", "--showmeminfo", "vram",
                     "--showtemp", "--showuse", "--json"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    # rocm-smi JSON format varies by version; handle common formats
                    for card_key, card_data in data.items():
                        if not isinstance(card_data, dict):
                            continue
                        info["available"] = True
                        info["vendor"] = "AMD"
                        info["name"] = card_data.get("Card series", card_data.get("Card Series", "AMD GPU"))
                        # VRAM
                        vram_total = card_data.get("VRAM Total Memory (B)", 0)
                        vram_used = card_data.get("VRAM Total Used Memory (B)", 0)
                        if vram_total:
                            info["vram_total_gb"] = int(vram_total) / (1024**3)
                            info["vram_used_gb"] = int(vram_used) / (1024**3)
                            info["vram_free_gb"] = info["vram_total_gb"] - info["vram_used_gb"]
                        # Temperature
                        temp = card_data.get("Temperature (Sensor edge) (C)", 0)
                        if temp:
                            info["temperature"] = int(float(str(temp)))
                        # Utilization
                        use = card_data.get("GPU use (%)", 0)
                        if use:
                            info["utilization"] = int(float(str(use)))
                        break  # First GPU only
            except Exception:
                pass

            # Fallback: non-JSON rocm-smi
            if not info["available"]:
                try:
                    result = subprocess.run(
                        ["rocm-smi"], capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0 and "GPU" in result.stdout:
                        info["available"] = True
                        info["vendor"] = "AMD"
                        info["name"] = "AMD GPU (ROCm)"
                except Exception:
                    pass

        return info

    @staticmethod
    def get_disk_info() -> Dict:
        """Get disk information for ai-models directory"""
        info = {"total_gb": 0, "free_gb": 0, "used_percent": 0}

        try:
            models_path = Path.home() / "ai-models"
            if not models_path.exists():
                models_path = Path.home()

            stat = os.statvfs(str(models_path))
            info["total_gb"] = (stat.f_blocks * stat.f_frsize) / (1024**3)
            info["free_gb"] = (stat.f_bavail * stat.f_frsize) / (1024**3)
            info["used_percent"] = ((info["total_gb"] - info["free_gb"]) / info["total_gb"] * 100) if info["total_gb"] > 0 else 0
        except Exception:
            pass

        return info

    @staticmethod
    def get_models_disk_usage() -> List[Dict]:
        """Get per-model disk usage breakdown from Ollama models directory"""
        models = []
        ollama_models = Path.home() / ".ollama" / "models" / "manifests" / "registry.ollama.ai" / "library"
        blobs_dir = Path.home() / ".ollama" / "models" / "blobs"

        try:
            if ollama_models.exists():
                for model_dir in sorted(ollama_models.iterdir()):
                    if model_dir.is_dir():
                        # Sum all blob sizes referenced by this model's manifests
                        total_size = 0
                        for manifest_file in model_dir.rglob("*"):
                            if manifest_file.is_file():
                                try:
                                    manifest = json.loads(manifest_file.read_text())
                                    for layer in manifest.get("layers", []):
                                        digest = layer.get("digest", "")
                                        if digest:
                                            blob_path = blobs_dir / digest.replace(":", "-")
                                            if blob_path.exists():
                                                total_size += blob_path.stat().st_size
                                except Exception:
                                    total_size += manifest_file.stat().st_size

                        if total_size > 0:
                            models.append({
                                "name": model_dir.name,
                                "size_gb": total_size / (1024**3),
                            })

            # Sort by size descending
            models.sort(key=lambda m: m["size_gb"], reverse=True)
        except Exception:
            pass

        return models

    @staticmethod
    def get_ollama_info() -> Dict:
        """Get Ollama status including running models"""
        info = {
            "installed": False,
            "version": "",
            "running": False,
            "models_count": 0,
            "running_models": [],
            "pid": None,
            "mem_mb": 0,
        }

        try:
            # Check version
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                info["installed"] = True
                info["version"] = result.stdout.strip().split()[-1] if result.stdout else ""

            # Check if running via API
            result2 = subprocess.run(
                ["curl", "-s", "http://localhost:11434/api/tags"],
                capture_output=True, text=True, timeout=5
            )
            info["running"] = result2.returncode == 0

            # Count models
            result3 = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=10
            )
            if result3.returncode == 0:
                lines = result3.stdout.strip().split("\n")
                info["models_count"] = max(0, len(lines) - 1)

            # Get running/loaded models via ps
            result4 = subprocess.run(
                ["curl", "-s", "http://localhost:11434/api/ps"],
                capture_output=True, text=True, timeout=5
            )
            if result4.returncode == 0 and result4.stdout.strip():
                try:
                    ps_data = json.loads(result4.stdout)
                    for model in ps_data.get("models", []):
                        name = model.get("name", "unknown")
                        size = model.get("size", 0)
                        vram = model.get("size_vram", 0)
                        info["running_models"].append({
                            "name": name,
                            "size_gb": size / (1024**3) if size else 0,
                            "vram_gb": vram / (1024**3) if vram else 0,
                        })
                except Exception:
                    pass

            # Get Ollama process info
            try:
                result5 = subprocess.run(
                    ["pgrep", "-f", "ollama serve"],
                    capture_output=True, text=True, timeout=3
                )
                if result5.returncode == 0 and result5.stdout.strip():
                    pid = result5.stdout.strip().split()[0]
                    info["pid"] = int(pid)
                    # Get memory usage from /proc
                    with open(f"/proc/{pid}/status", "r") as f:
                        for line in f:
                            if line.startswith("VmRSS:"):
                                mem_kb = int(line.split()[1])
                                info["mem_mb"] = mem_kb / 1024
                                break
            except Exception:
                pass

        except Exception:
            pass

        return info

    @staticmethod
    def get_warnings(gpu: Dict, mem: Dict, disk: Dict) -> List[Dict]:
        """Generate proactive system warnings."""
        warnings = []

        # Low disk space
        if disk.get("free_gb", 999) < 10:
            warnings.append({
                "level": "error",
                "text": f"Espacio en disco MUY bajo: {disk['free_gb']:.1f} GB libres"
            })
        elif disk.get("free_gb", 999) < 30:
            warnings.append({
                "level": "warning",
                "text": f"Espacio en disco bajo: {disk['free_gb']:.1f} GB libres"
            })

        # High GPU temperature
        if gpu.get("available") and gpu.get("temperature", 0) > 85:
            warnings.append({
                "level": "error",
                "text": f"GPU MUY caliente: {gpu['temperature']}C - riesgo de throttling"
            })
        elif gpu.get("available") and gpu.get("temperature", 0) > 75:
            warnings.append({
                "level": "warning",
                "text": f"GPU caliente: {gpu['temperature']}C"
            })

        # High RAM usage
        if mem.get("used_percent", 0) > 90:
            warnings.append({
                "level": "error",
                "text": f"RAM casi llena: {mem['used_percent']:.0f}% en uso"
            })
        elif mem.get("used_percent", 0) > 80:
            warnings.append({
                "level": "warning",
                "text": f"RAM alta: {mem['used_percent']:.0f}% en uso"
            })

        # Swap usage
        if mem.get("swap_used_gb", 0) > 1:
            warnings.append({
                "level": "warning",
                "text": f"Usando swap: {mem['swap_used_gb']:.1f} GB - rendimiento reducido"
            })

        # Low VRAM
        if gpu.get("available") and gpu.get("vram_free_gb", 999) < 1:
            warnings.append({
                "level": "warning",
                "text": f"VRAM casi llena: {gpu['vram_free_gb']:.1f} GB libres"
            })

        return warnings


def estimate_model_performance(model_size_gb: float, gpu_info: Dict, ram_info: Dict) -> Dict:
    """Estimate how well a model will run"""
    result = {
        "can_run": False,
        "recommended": False,
        "speed_rating": "Unknown",
        "will_use_gpu": False,
        "warnings": [],
        "tips": []
    }

    vram_free = gpu_info.get("vram_free_gb", 0)
    vram_total = gpu_info.get("vram_total_gb", 0)
    ram_available = ram_info.get("available_gb", 0)
    has_gpu = gpu_info.get("available", False)

    total_memory = vram_free + ram_available
    if total_memory < model_size_gb * 1.1:
        result["can_run"] = False
        result["speed_rating"] = "NO PUEDE EJECUTAR"
        result["warnings"].append(f"Memoria insuficiente. Necesitas {model_size_gb:.1f}GB, tienes {total_memory:.1f}GB disponibles")
        return result

    result["can_run"] = True

    if has_gpu and vram_free >= model_size_gb * 1.05:
        result["will_use_gpu"] = True
        result["recommended"] = True

        if vram_free >= model_size_gb * 1.5:
            result["speed_rating"] = "EXCELENTE"
            result["tips"].append("El modelo cabe completamente en GPU - maxima velocidad!")
        elif vram_free >= model_size_gb * 1.2:
            result["speed_rating"] = "MUY BUENO"
            result["tips"].append("Buen margen de VRAM disponible")
        else:
            result["speed_rating"] = "BUENO"
            result["tips"].append("Ajustado pero funcionara bien en GPU")

    elif has_gpu and vram_free >= model_size_gb * 0.5:
        result["will_use_gpu"] = True
        result["speed_rating"] = "ACEPTABLE"
        result["warnings"].append("Parte del modelo usara RAM (mas lento)")
        result["tips"].append("Considera un modelo mas pequeno para mejor rendimiento")

    elif ram_available >= model_size_gb * 1.2:
        result["will_use_gpu"] = False
        result["speed_rating"] = "LENTO"
        result["warnings"].append("Ejecutara en CPU - respuestas lentas (30-60 seg)")
        result["tips"].append("Instala drivers NVIDIA para usar GPU")

    else:
        result["speed_rating"] = "MUY LENTO"
        result["warnings"].append("Memoria muy justa - puede ir muy lento o fallar")
        result["tips"].append("Usa un modelo mas pequeno (Q3_K_S)")

    return result


class SpecCard(ctk.CTkFrame):
    """Card showing a system specification"""

    def __init__(self, parent, title: str, icon: str, **kwargs):
        super().__init__(
            parent,
            fg_color=COLORS["bg_card"],
            border_color=COLORS["border_green"],
            border_width=1,
            corner_radius=RADIUS["lg"],
            **kwargs
        )

        self.grid_columnconfigure(0, weight=1)
        self._row_count = 0

        # Header
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_tertiary"], corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")

        ctk.CTkLabel(
            header,
            text=f" {icon} {title}",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            text_color=COLORS["matrix_green_bright"]
        ).pack(anchor="w", padx=15, pady=10)

        # Content area
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=1, column=0, sticky="ew", padx=15, pady=15)
        self.content.grid_columnconfigure(1, weight=1)

    def add_row(self, label: str, value: str, row: int, highlight: bool = False,
                color: str = None):
        """Add a data row"""
        if color:
            val_color = color
        elif highlight:
            val_color = COLORS["matrix_green_bright"]
        else:
            val_color = COLORS["matrix_green"]

        ctk.CTkLabel(
            self.content,
            text=label,
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color=COLORS["text_muted"]
        ).grid(row=row, column=0, sticky="w", pady=3)

        ctk.CTkLabel(
            self.content,
            text=value,
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=val_color
        ).grid(row=row, column=1, sticky="e", pady=3)

    def add_progress(self, label: str, value: float, row: int,
                     warn_threshold: float = 80, error_threshold: float = 90):
        """Add a progress bar row with color thresholds"""
        ctk.CTkLabel(
            self.content,
            text=label,
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color=COLORS["text_muted"]
        ).grid(row=row, column=0, sticky="w", pady=3)

        # Choose color based on value
        if value >= error_threshold:
            prog_color = COLORS["error"]
        elif value >= warn_threshold:
            prog_color = COLORS["warning"]
        else:
            prog_color = COLORS["matrix_green"]

        bar = MatrixProgressBar(self.content, width=150, height=12)
        bar.configure(progress_color=prog_color)
        bar.set(value / 100)
        bar.grid(row=row, column=1, sticky="e", pady=3)


class SystemPanel(ctk.CTkFrame):
    """System specifications panel with auto-refresh and diagnostics"""

    def __init__(self, parent, **kwargs):
        kwargs.setdefault("fg_color", COLORS["bg_primary"])
        kwargs.setdefault("corner_radius", 0)
        super().__init__(parent, **kwargs)

        self.system_info = {}
        self._auto_refresh_id = None
        self._setup_ui()
        self.after(100, self._load_info)

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header with buttons
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        header = TerminalHeader(header_frame, "ESPECIFICACIONES", "system.info")
        header.grid(row=0, column=0, sticky="ew")

        # Button row
        btn_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=1, padx=10, pady=5, sticky="e")

        self.refresh_btn = ctk.CTkButton(
            btn_frame,
            text=f"{DECORATIONS['block_med']} REFRESH",
            font=ctk.CTkFont(family="Consolas", size=10),
            width=80, height=24,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            border_color=COLORS["matrix_green_dim"],
            border_width=1,
            text_color=COLORS["matrix_green"],
            command=self._refresh
        )
        self.refresh_btn.pack(side="left", padx=(0, 5))

        self.export_btn = ctk.CTkButton(
            btn_frame,
            text=f"{DECORATIONS['arrow_r']} EXPORT",
            font=ctk.CTkFont(family="Consolas", size=10),
            width=70, height=24,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            border_color=COLORS["matrix_green_dim"],
            border_width=1,
            text_color=COLORS["matrix_green"],
            command=self._export_info
        )
        self.export_btn.pack(side="left")

        # Auto-refresh indicator
        self.auto_refresh_label = ctk.CTkLabel(
            header_frame,
            text="",
            font=ctk.CTkFont(family="Consolas", size=9),
            text_color=COLORS["text_dim"],
        )
        self.auto_refresh_label.grid(row=1, column=0, columnspan=2, sticky="e", padx=15)

        # Scrollable content
        self.content = MatrixScrollableFrame(self, fg_color=COLORS["bg_primary"], border_width=0)
        self.content.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.content.grid_columnconfigure(0, weight=1)

        # Loading indicator
        self.loading_label = MatrixLabel(
            self.content,
            text=f"{DECORATIONS['block_med']} Analizando sistema...",
            size="lg"
        )
        self.loading_label.pack(pady=50)

    def _start_auto_refresh(self):
        """Start periodic auto-refresh"""
        self._stop_auto_refresh()
        self._auto_refresh_id = self.after(AUTO_REFRESH_INTERVAL, self._auto_refresh_tick)

    def _stop_auto_refresh(self):
        """Stop periodic auto-refresh"""
        if self._auto_refresh_id:
            self.after_cancel(self._auto_refresh_id)
            self._auto_refresh_id = None

    def _auto_refresh_tick(self):
        """Auto-refresh callback"""
        self._load_info(silent=True)
        self._auto_refresh_id = self.after(AUTO_REFRESH_INTERVAL, self._auto_refresh_tick)

    def _load_info(self, silent: bool = False):
        """Load system info in background"""
        def load():
            self.system_info = {
                "cpu": SystemInfo.get_cpu_info(),
                "memory": SystemInfo.get_memory_info(),
                "gpu": SystemInfo.get_gpu_info(),
                "disk": SystemInfo.get_disk_info(),
                "ollama": SystemInfo.get_ollama_info(),
            }
            self.system_info["warnings"] = SystemInfo.get_warnings(
                self.system_info["gpu"],
                self.system_info["memory"],
                self.system_info["disk"],
            )
            self.system_info["models_disk"] = SystemInfo.get_models_disk_usage()
            self.after(0, lambda: self._display_info(silent))

        threading.Thread(target=load, daemon=True).start()

    def _display_info(self, silent: bool = False):
        """Display gathered info"""
        # Start auto-refresh if not already running
        if self._auto_refresh_id is None:
            self._start_auto_refresh()

        # Clear everything
        for widget in self.content.winfo_children():
            widget.destroy()

        cpu = self.system_info["cpu"]
        mem = self.system_info["memory"]
        gpu = self.system_info["gpu"]
        disk = self.system_info["disk"]
        ollama = self.system_info["ollama"]
        warnings = self.system_info.get("warnings", [])
        models_disk = self.system_info.get("models_disk", [])

        # Update auto-refresh timestamp
        from datetime import datetime
        self.auto_refresh_label.configure(
            text=f"Auto-refresh: 30s | Last: {datetime.now().strftime('%H:%M:%S')}"
        )

        # ═══════════════════════════════════════════════════════════
        # WARNINGS (if any)
        # ═══════════════════════════════════════════════════════════
        if warnings:
            warn_card = ctk.CTkFrame(
                self.content,
                fg_color="#1a1000" if any(w["level"] == "error" for w in warnings) else COLORS["bg_card"],
                border_color=COLORS["error"] if any(w["level"] == "error" for w in warnings) else COLORS["warning"],
                border_width=2,
                corner_radius=RADIUS["lg"],
            )
            warn_card.pack(fill="x", pady=(0, 10))

            warn_header = ctk.CTkFrame(warn_card, fg_color="transparent")
            warn_header.pack(fill="x", padx=15, pady=(10, 5))

            ctk.CTkLabel(
                warn_header,
                text=f" {DECORATIONS['cross']} ADVERTENCIAS DEL SISTEMA",
                font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
                text_color=COLORS["warning"],
            ).pack(anchor="w")

            for w in warnings:
                color = COLORS["error"] if w["level"] == "error" else COLORS["warning"]
                icon = DECORATIONS["cross"] if w["level"] == "error" else DECORATIONS["circle"]
                ctk.CTkLabel(
                    warn_card,
                    text=f"  {icon} {w['text']}",
                    font=ctk.CTkFont(family="Consolas", size=12),
                    text_color=color,
                    anchor="w",
                ).pack(fill="x", padx=15, pady=2)

            # Bottom padding
            ctk.CTkFrame(warn_card, fg_color="transparent", height=8).pack()

        # ═══════════════════════════════════════════════════════════
        # RESUMEN DE CAPACIDAD
        # ═══════════════════════════════════════════════════════════
        summary = self._create_summary_card()
        summary.pack(fill="x", pady=(0, 15))

        # ═══════════════════════════════════════════════════════════
        # GPU
        # ═══════════════════════════════════════════════════════════
        vendor = gpu.get("vendor", "NVIDIA") if gpu["available"] else "GPU"
        gpu_card = SpecCard(self.content, f"GPU ({vendor})", DECORATIONS["block"])
        gpu_card.pack(fill="x", pady=(0, 10))

        if gpu["available"]:
            gpu_card.add_row("Modelo:", gpu["name"], 0, highlight=True)
            gpu_card.add_row("VRAM Total:", f"{gpu['vram_total_gb']:.1f} GB", 1)
            gpu_card.add_row("VRAM Libre:", f"{gpu['vram_free_gb']:.1f} GB", 2, highlight=True)
            gpu_card.add_row("VRAM Usado:", f"{gpu['vram_used_gb']:.1f} GB", 3)

            # Temperature with color coding
            temp = gpu["temperature"]
            if temp > 85:
                temp_color = COLORS["error"]
            elif temp > 75:
                temp_color = COLORS["warning"]
            else:
                temp_color = COLORS["matrix_green"]
            gpu_card.add_row("Temperatura:", f"{temp}C", 4, color=temp_color)

            gpu_card.add_row("Uso GPU:", f"{gpu['utilization']}%", 5)
            gpu_card.add_progress("Uso VRAM:", (gpu["vram_used_gb"] / gpu["vram_total_gb"] * 100) if gpu["vram_total_gb"] > 0 else 0, 6)
            gpu_card.add_row("Driver:", gpu["driver_version"], 7)
            if gpu["cuda_version"]:
                gpu_card.add_row("CUDA:", gpu["cuda_version"], 8)
        else:
            gpu_card.add_row("Estado:", "No detectada", 0)
            gpu_card.add_row("Nota:", "Instala drivers NVIDIA o AMD ROCm", 1)

        # ═══════════════════════════════════════════════════════════
        # RAM
        # ═══════════════════════════════════════════════════════════
        ram_card = SpecCard(self.content, "MEMORIA RAM", DECORATIONS["block"])
        ram_card.pack(fill="x", pady=(0, 10))

        ram_card.add_row("Total:", f"{mem['total_gb']:.1f} GB", 0)
        ram_card.add_row("Disponible:", f"{mem['available_gb']:.1f} GB", 1, highlight=True)
        ram_card.add_progress("Uso:", mem['used_percent'], 2)
        if mem.get("swap_total_gb", 0) > 0:
            ram_card.add_row("Swap Total:", f"{mem['swap_total_gb']:.1f} GB", 3)
            swap_color = COLORS["warning"] if mem["swap_used_gb"] > 1 else COLORS["matrix_green"]
            ram_card.add_row("Swap Usado:", f"{mem['swap_used_gb']:.1f} GB", 4, color=swap_color)

        # ═══════════════════════════════════════════════════════════
        # CPU
        # ═══════════════════════════════════════════════════════════
        cpu_card = SpecCard(self.content, "PROCESADOR (CPU)", DECORATIONS["block"])
        cpu_card.pack(fill="x", pady=(0, 10))

        cpu_card.add_row("Modelo:", cpu["name"][:50], 0)
        cpu_card.add_row("Nucleos:", str(cpu["cores"]), 1)

        # ═══════════════════════════════════════════════════════════
        # DISCO
        # ═══════════════════════════════════════════════════════════
        disk_card = SpecCard(self.content, "ALMACENAMIENTO", DECORATIONS["block"])
        disk_card.pack(fill="x", pady=(0, 10))

        disk_card.add_row("Espacio Total:", f"{disk['total_gb']:.0f} GB", 0)
        free_color = COLORS["error"] if disk["free_gb"] < 10 else (COLORS["warning"] if disk["free_gb"] < 30 else None)
        disk_card.add_row("Espacio Libre:", f"{disk['free_gb']:.0f} GB", 1,
                          highlight=free_color is None, color=free_color)
        disk_card.add_progress("Uso:", disk['used_percent'], 2)

        # Models disk breakdown
        if models_disk:
            row = 3
            disk_card.add_row("", "", row)  # spacer
            row += 1
            disk_card.add_row("Modelos Ollama:", "", row)
            row += 1
            total_models_size = 0
            for md in models_disk[:8]:  # Show top 8
                disk_card.add_row(f"  {md['name']}:", f"{md['size_gb']:.1f} GB", row)
                total_models_size += md["size_gb"]
                row += 1
            if len(models_disk) > 8:
                remaining = sum(m["size_gb"] for m in models_disk[8:])
                disk_card.add_row(f"  +{len(models_disk)-8} mas:", f"{remaining:.1f} GB", row)
                total_models_size += remaining
                row += 1
            disk_card.add_row("  TOTAL:", f"{total_models_size:.1f} GB", row, highlight=True)

        # ═══════════════════════════════════════════════════════════
        # OLLAMA
        # ═══════════════════════════════════════════════════════════
        ollama_card = SpecCard(self.content, "OLLAMA", DECORATIONS["block"])
        ollama_card.pack(fill="x", pady=(0, 10))

        ollama_card.add_row("Instalado:", "Si" if ollama["installed"] else "No", 0)
        if ollama["installed"]:
            ollama_card.add_row("Version:", ollama["version"], 1)
            status_color = COLORS["success"] if ollama["running"] else COLORS["error"]
            ollama_card.add_row("Servidor:", "Activo" if ollama["running"] else "Inactivo", 2,
                                color=status_color)
            ollama_card.add_row("Modelos instalados:", str(ollama["models_count"]), 3)

            row = 4
            # Process info
            if ollama.get("pid"):
                ollama_card.add_row("PID:", str(ollama["pid"]), row)
                row += 1
                if ollama.get("mem_mb", 0) > 0:
                    ollama_card.add_row("Memoria proceso:", f"{ollama['mem_mb']:.0f} MB", row)
                    row += 1

            # Running/loaded models
            if ollama.get("running_models"):
                ollama_card.add_row("", "", row)  # spacer
                row += 1
                ollama_card.add_row("Modelos cargados:", "", row)
                row += 1
                for rm in ollama["running_models"]:
                    vram_str = f" (VRAM: {rm['vram_gb']:.1f}GB)" if rm.get("vram_gb") else ""
                    ollama_card.add_row(
                        f"  {rm['name']}:",
                        f"{rm['size_gb']:.1f} GB{vram_str}",
                        row, highlight=True
                    )
                    row += 1

    def _create_summary_card(self) -> ctk.CTkFrame:
        """Create summary card with recommendations"""
        gpu = self.system_info["gpu"]
        mem = self.system_info["memory"]

        card = ctk.CTkFrame(
            self.content,
            fg_color=COLORS["bg_secondary"],
            border_color=COLORS["matrix_green"],
            border_width=2,
            corner_radius=RADIUS["lg"]
        )

        header = ctk.CTkFrame(card, fg_color=COLORS["bg_tertiary"], corner_radius=0)
        header.pack(fill="x")

        ctk.CTkLabel(
            header,
            text=f" {DECORATIONS['star']} RESUMEN - QUE MODELOS PUEDO USAR?",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            text_color=COLORS["matrix_green_bright"]
        ).pack(anchor="w", padx=15, pady=10)

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=20, pady=15)

        vram = gpu.get("vram_free_gb", 0)
        ram = mem.get("available_gb", 0)
        has_gpu = gpu.get("available", False)

        if has_gpu:
            summary_text = f"""
{DECORATIONS['check']} GPU Detectada: {gpu['name']}
{DECORATIONS['check']} VRAM Disponible: {vram:.1f} GB
{DECORATIONS['check']} RAM Disponible: {ram:.1f} GB

{DECORATIONS['arrow_r']} MODELOS RECOMENDADOS PARA TU SISTEMA:
"""
            if vram >= 10:
                summary_text += f"""
   {DECORATIONS['star']} Modelos 13B Q5/Q6 - EXCELENTE rendimiento
   {DECORATIONS['star']} Modelos 7B Q8 - PERFECTO
   {DECORATIONS['star']} Modelos 7B Q4/Q5 - MUY RAPIDO
"""
            elif vram >= 6:
                summary_text += f"""
   {DECORATIONS['star']} Modelos 7B Q4_K_M - RECOMENDADO (4-5GB)
   {DECORATIONS['star']} Modelos 7B Q5_K_S - Bueno si cabe
   {DECORATIONS['circle']} Modelos 13B Q3 - Funcionara pero ajustado
"""
            elif vram >= 4:
                summary_text += f"""
   {DECORATIONS['star']} Modelos 7B Q3_K_M - RECOMENDADO (3-4GB)
   {DECORATIONS['star']} Modelos 7B Q4_K_S - Deberia funcionar
   {DECORATIONS['cross']} Modelos 13B+ - Demasiado grandes
"""
            else:
                summary_text += f"""
   {DECORATIONS['star']} Modelos 7B Q2_K o Q3_K_S - Lo mas ligero
   {DECORATIONS['circle']} Puede necesitar usar RAM tambien
"""
        else:
            summary_text = f"""
{DECORATIONS['cross']} GPU: No detectada
{DECORATIONS['check']} RAM Disponible: {ram:.1f} GB

{DECORATIONS['arrow_r']} SIN GPU - Ejecutara en CPU (mas lento)

   {DECORATIONS['star']} Modelos 7B Q3_K_S - Mejor opcion sin GPU
   {DECORATIONS['circle']} Espera 30-60 segundos por respuesta
   {DECORATIONS['prompt']} TIP: Instala drivers NVIDIA para acelerar
"""

        summary_label = ctk.CTkLabel(
            content,
            text=summary_text,
            font=ctk.CTkFont(family="Consolas", size=13),
            text_color=COLORS["matrix_green"],
            justify="left",
            anchor="w",
            wraplength=600
        )
        summary_label.pack(fill="x")

        def _update_summary_wrap(event=None):
            try:
                summary_label.configure(wraplength=max(200, content.winfo_width() - 60))
            except Exception:
                pass

        content.bind("<Configure>", _update_summary_wrap, add="+")

        return card

    def _refresh(self):
        """Manual refresh"""
        for widget in self.content.winfo_children():
            widget.destroy()

        self.loading_label = MatrixLabel(
            self.content,
            text=f"{DECORATIONS['block_med']} Actualizando...",
            size="lg"
        )
        self.loading_label.pack(pady=50)

        self.after(100, self._load_info)

    def _export_info(self):
        """Export system info as text file"""
        from tkinter import filedialog
        from datetime import datetime

        if not self.system_info:
            return

        path = filedialog.asksaveasfilename(
            title="Export System Info",
            defaultextension=".txt",
            filetypes=[("Text", "*.txt"), ("All files", "*.*")],
            initialfile=f"system_info_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        )
        if not path:
            return

        cpu = self.system_info.get("cpu", {})
        mem = self.system_info.get("memory", {})
        gpu = self.system_info.get("gpu", {})
        disk = self.system_info.get("disk", {})
        ollama = self.system_info.get("ollama", {})
        warnings = self.system_info.get("warnings", [])

        lines = [
            "=" * 50,
            "DRAGO MODEL RUNNER - System Info",
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Platform: {platform.system()} {platform.release()}",
            "=" * 50,
            "",
            "--- CPU ---",
            f"Model: {cpu.get('name', 'N/A')}",
            f"Cores: {cpu.get('cores', 'N/A')}",
            "",
            "--- MEMORY ---",
            f"Total: {mem.get('total_gb', 0):.1f} GB",
            f"Available: {mem.get('available_gb', 0):.1f} GB",
            f"Used: {mem.get('used_percent', 0):.1f}%",
            f"Swap Total: {mem.get('swap_total_gb', 0):.1f} GB",
            f"Swap Used: {mem.get('swap_used_gb', 0):.1f} GB",
            "",
            "--- GPU ---",
        ]

        if gpu.get("available"):
            lines.extend([
                f"Vendor: {gpu.get('vendor', 'N/A')}",
                f"Model: {gpu.get('name', 'N/A')}",
                f"VRAM Total: {gpu.get('vram_total_gb', 0):.1f} GB",
                f"VRAM Free: {gpu.get('vram_free_gb', 0):.1f} GB",
                f"VRAM Used: {gpu.get('vram_used_gb', 0):.1f} GB",
                f"Temperature: {gpu.get('temperature', 0)}C",
                f"Utilization: {gpu.get('utilization', 0)}%",
                f"Driver: {gpu.get('driver_version', 'N/A')}",
                f"CUDA: {gpu.get('cuda_version', 'N/A')}",
            ])
        else:
            lines.append("Not detected")

        lines.extend([
            "",
            "--- DISK ---",
            f"Total: {disk.get('total_gb', 0):.0f} GB",
            f"Free: {disk.get('free_gb', 0):.0f} GB",
            f"Used: {disk.get('used_percent', 0):.1f}%",
            "",
            "--- OLLAMA ---",
            f"Installed: {ollama.get('installed', False)}",
            f"Version: {ollama.get('version', 'N/A')}",
            f"Running: {ollama.get('running', False)}",
            f"Models: {ollama.get('models_count', 0)}",
        ])

        if ollama.get("pid"):
            lines.append(f"PID: {ollama['pid']}")
            lines.append(f"Memory: {ollama.get('mem_mb', 0):.0f} MB")

        if ollama.get("running_models"):
            lines.append("")
            lines.append("Loaded models:")
            for rm in ollama["running_models"]:
                lines.append(f"  {rm['name']} - {rm['size_gb']:.1f} GB")

        if warnings:
            lines.extend(["", "--- WARNINGS ---"])
            for w in warnings:
                lines.append(f"[{w['level'].upper()}] {w['text']}")

        lines.append("")

        Path(path).write_text("\n".join(lines), encoding="utf-8")

    def get_performance_estimate(self, model_size_gb: float) -> Dict:
        """Get performance estimate for a model"""
        if not self.system_info:
            return {"can_run": False, "speed_rating": "Unknown", "warnings": ["Info no cargada"]}

        return estimate_model_performance(
            model_size_gb,
            self.system_info.get("gpu", {}),
            self.system_info.get("memory", {})
        )
